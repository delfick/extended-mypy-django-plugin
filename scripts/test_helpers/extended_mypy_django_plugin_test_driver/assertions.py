import fnmatch


def assert_glob_lines(got: str, expect: str) -> None:
    message = [line.strip() for line in got.strip().replace("\r\n", "\n").split("\n")]
    want = [line.strip() for line in expect.strip().split("\n")]

    print("GOT >>" + "=" * 74)
    print()
    print("\n".join(message))
    print()
    print("WANT >>" + "-" * 73)
    print()
    print("\n".join(want))

    count = 1
    while want:
        line = want[0]
        if not message:
            assert False, f"Ran out of lines, stopped at [{count}] '{want[0]}'"

        if message[0] == line or fnmatch.fnmatch(message[0], line):
            count += 1
            want.pop(0)

        message.pop(0)

    if want:
        assert False, f"Didn't match all the lines, stopped at [{count}] '{want[0]}'"
