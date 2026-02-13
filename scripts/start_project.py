#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

SERVICES = [
    "db",
    "mqtt_broker",
    "coap-gps",
    "coap-batt",
    "coap-temp",
    "coap-leader",
    "coap-routeur",
    "backend",
    "frontend",
]


def run(cmd, env=None):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def main():
    parser = argparse.ArgumentParser(description="Start Zolis docker stack")
    parser.add_argument("--build", action="store_true", help="Rebuild images and recreate containers")
    parser.add_argument("--logs", action="store_true", help="Follow key logs after startup")
    parser.add_argument(
        "--strict-thread",
        action="store_true",
        help="Force OpenThread strict mode (IPv6 only)",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("ZOLIS_OT_REQUIRED", "0")
    env.setdefault("ZOLIS_STRICT_THREAD", "0")

    if args.strict_thread:
        env["ZOLIS_OT_REQUIRED"] = "1"
        env["ZOLIS_STRICT_THREAD"] = "1"

    print(
        "Starting Zolis with "
        f"ZOLIS_OT_REQUIRED={env['ZOLIS_OT_REQUIRED']} "
        f"ZOLIS_STRICT_THREAD={env['ZOLIS_STRICT_THREAD']}"
    )

    up_cmd = ["docker", "compose", "up", "-d"]
    if args.build:
        up_cmd.extend(["--build", "--force-recreate"])
    up_cmd.extend(SERVICES)

    try:
        run(up_cmd, env=env)
        run(["docker", "compose", "ps"], env=env)
    except FileNotFoundError:
        print("Error: docker command not found. Install/enable Docker first.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        return exc.returncode

    print("Frontend: http://127.0.0.1:5000")
    print("Tip: curl -X POST http://127.0.0.1:5000/api/backend/collect")

    if args.logs:
        try:
            run(["docker", "compose", "logs", "-f", "backend", "frontend", "coap-routeur", "coap-leader"], env=env)
        except subprocess.CalledProcessError as exc:
            return exc.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
