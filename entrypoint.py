#!/usr/bin/env python3

import argparse
import subprocess
import os
import shutil


def git_clone(args):
    url = "https://github.com/{user}/spark.git".format(user=args.user)

    subprocess.check_call(
        ["git", "clone", "--depth", "1", "--branch", args.branch, url]
    )
    os.chdir("spark")
    if args.commit:
        subprocess.check_call(["git", "checkout", args.commit])

    subprocess.check_call(["git", "rev-parse", "HEAD"])


def build_and_test(args):
    git_clone(args)

    if args.public_key:
        wget = subprocess.Popen(
            ["wget", "-qO", "-", args.public_key], stdout=subprocess.PIPE
        )
        subprocess.check_call(["gpg", "--import"], stdin=wget.stdout)

        verify = subprocess.Popen(
            ["git", "verify-commit", "-v", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        verify_status_code = verify.wait()
        for line in verify.stdout:
            print(line.decode("utf-8"))

        # Older versions of git return 1 if signature is valid, but not trusted
        if verify_status_code:
            verify_stderr = [line.decode("UTF-8") for line in verify.stderr]
            for line in verify_stderr:
                print(line)

            if not verify_stderr:
                print(
                    "verify-commit returned {} but no error message. "
                    "Missing signature?".format(verify_status_code)
                )

            elif not any("Good signature" in line for line in verify_stderr):
                exit(1)

    subprocess.check_call(
        ["build/mvn", "-DskipTests", "-Phive", "-Psparkr", "clean", "package"]
    )
    subprocess.check_call(["Rscript", "/scripts/show_session_info.R"])
    subprocess.check_call(["R/create-rd.sh"])
    subprocess.check_call(["R/create-docs.sh"])
    subprocess.check_call(["R/check-cran.sh"])
    subprocess.check_call(["R/run-tests.sh"])


def resolve_dependencies(args):
    git_clone(args)

    subprocess.check_call(["build/mvn", "dependency:resolve", "-U"])
    os.chdir("..")
    shutil.rmtree("spark")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("user", help="GitHub username")
    parser.add_argument("--branch", type=str, default="master", help="Branch to fetch")
    parser.add_argument("--commit", help="Commit hash")
    parser.add_argument(
        "--action",
        choices=["build-and-test", "resolve-dependencies"],
        default="build-and-test",
    )
    parser.add_argument(
        "--public-key", help="URL pointing to GPG key used to sign the commit"
    )

    args = parser.parse_args()

    if args.action == "build-and-test":
        build_and_test(args)
    else:
        resolve_dependencies(args)


if __name__ == "__main__":
    main()
