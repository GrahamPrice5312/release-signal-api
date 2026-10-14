import argparse
import json

from release_signal.infrai_email import InfraiEmail
from release_signal.release_campaign import BuildEvent, ReleaseCampaign


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one release note email")
    parser.add_argument("recipient")
    parser.add_argument("--project", default="FrameForge")
    parser.add_argument("--tag", default="v1.4.0")
    parser.add_argument("--commit", default="8c4f31a")
    parser.add_argument("--changelog", default="Faster preview renders and clearer build logs.")
    args = parser.parse_args()

    operation = ReleaseCampaign(InfraiEmail()).publish(
        BuildEvent(args.project, args.tag, args.commit, args.changelog),
        args.recipient,
    )
    print(json.dumps(operation.__dict__, indent=2))


if __name__ == "__main__":
    main()
