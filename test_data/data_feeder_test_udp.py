#!/usr/bin/env python3

# Copyright (c) Mike Nye, Fred Clausen
#
# Licensed under the MIT license: https://opensource.org/licenses/MIT
# Permission is granted to use, copy, modify, and redistribute the work.
# Full license information available in the project LICENSE file.
#

import json
import random
import socket
import time
import sys
import argparse
from threading import Thread, Event  # noqa: E402
from collections import deque  # noqa: E402

thread_stop_event = Event()


def UDPSocketListener(port, queue):
    global thread_stop_event
    while not thread_stop_event.is_set():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.bind(("", port))
            data, _ = sock.recvfrom(25000)
            if data:
                try:
                    data = json.loads(data.decode("utf-8"))
                    queue.append(data)
                except Exception as e:
                    print(f"Invalid data received: {e}")
        except socket.timeout:
            pass
        except Exception as e:
            print(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test data feeder")
    parser.add_argument(
        "--check-for-dupes", action="store_true", help="Check for duplicate packets"
    )

    parser.add_argument(
        "--check-for-no-proxy-id", action="store_true", help="No proxy id"
    )
    parser.add_argument("--check-for-station-id", type=str, nargs="*", default="")
    parser.add_argument("--check-data-continuity", action="store_true")

    args = parser.parse_args()
    TEST_PASSED = True
    test_messages = []
    received_messages_queue_acars = deque()
    received_messages_queue_vdlm = deque()
    number_of_expected_acars_messages = 0
    number_of_expected_vdlm_messages = 0
    check_for_dupes = args.check_for_dupes
    check_for_station_id = (
        args.check_for_station_id[0] if args.check_for_station_id else None
    )
    check_for_no_proxy_id = args.check_for_no_proxy_id
    check_data_continuity = args.check_data_continuity

    with open("acars_other", "r") as acars:
        for line in acars:
            test_messages.append(json.loads(line))
            number_of_expected_acars_messages += 1

    with open("vdlm2_other", "r") as vdlm:
        for line in vdlm:
            test_messages.append(json.loads(line))
            number_of_expected_vdlm_messages += 1

    # sort the test_messages array randomly

    random.shuffle(test_messages)

    # Socket ports
    # inputs ACARS
    udp_acars_port = 15550
    # inputs VDLM
    udp_vdlm_port = 15555

    # Remote listening ports
    # ACARS
    udp_acars_remote_port = 15551
    # VDLM
    udp_vdlm_remote_port = 15556

    remote_ip = "127.0.0.1"

    # VDLM2
    thread_vdlm2_udp_listener = Thread(
        target=UDPSocketListener, args=(udp_vdlm_port, received_messages_queue_vdlm)
    )
    thread_vdlm2_udp_listener.start()

    # ACARS

    thread_acars_udp_listener = Thread(
        target=UDPSocketListener, args=(udp_acars_port, received_messages_queue_acars)
    )
    thread_acars_udp_listener.start()

    # create all of the output sockets
    # UDP
    acars_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    acars_sock.bind((remote_ip, 0))

    vdlm_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    vdlm_sock.bind((remote_ip, 0))

    # # # TCP
    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sock.bind((remote_ip, 25555))

    print(
        f"STARTING UDP SEND/RECEIVE {'DUPLICATION ' if check_for_dupes else ''}TEST\n\n"
    )
    message_count = 0
    duplicated = 0
    for message in test_messages:
        # UDP
        print(f"Sending message {message_count + 1}")
        # Randomly decide if the message should be sent twice
        if random.randint(0, 10) < 3:
            send_twice = True
            duplicated += 1
        else:
            send_twice = False

        if "vdl2" in message:
            # replace message["vdlm"]["t"]["sec"] with current unix epoch time
            message["vdl2"]["t"]["sec"] = int(time.time())
            vdlm_sock.sendto(
                json.dumps(message).encode() + b"\n", (remote_ip, udp_vdlm_remote_port)
            )
            if send_twice:
                time.sleep(0.2)
                print("Sending VDLM duplicate")
                vdlm_sock.sendto(
                    json.dumps(message).encode() + b"\n",
                    (remote_ip, udp_vdlm_remote_port),
                )
        else:
            # We are rounding to avoid an issue where acars_router will truncate the time
            # and thus the continunity check will fail even though it's good (sort of)
            message["timestamp"] = round(float(time.time()), 3)
            acars_sock.sendto(
                json.dumps(message).encode() + b"\n", (remote_ip, udp_acars_remote_port)
            )
            if send_twice:
                time.sleep(0.2)
                print("Sending ACARS duplicate")
                acars_sock.sendto(
                    json.dumps(message).encode() + b"\n",
                    (remote_ip, udp_acars_remote_port),
                )

        message_count += 1
        time.sleep(0.5)

    time.sleep(5)
    print(
        f"UDP SEND/RECEIVE {'DUPLICATION' if check_for_dupes else ''}TEST COMPLETE\n\n"
    )
    print(f"Sent {message_count} original messages")
    print(f"Sent {duplicated} duplicates")
    print(f"Sent {number_of_expected_acars_messages} of non dup ACARS messages")
    print(f"Sent {number_of_expected_vdlm_messages} of non dup VDLM messages")
    print(f"Sent {message_count + duplicated} total messages")
    print(
        f"Expected number of messages {number_of_expected_acars_messages + number_of_expected_vdlm_messages + (duplicated if not check_for_dupes else 0)}"
    )
    print(
        f"Received number of messages {len(received_messages_queue_acars) + len(received_messages_queue_vdlm)}"
    )

    if len(received_messages_queue_acars) + len(
        received_messages_queue_vdlm
    ) == number_of_expected_acars_messages + number_of_expected_vdlm_messages + (
        duplicated if not check_for_dupes else 0
    ):
        print(
            f"UDP SEND/RECEIVE {'DUPLICATION ' if check_for_dupes else ''}TEST PASSED"
        )
    else:
        print(
            f"UDP SEND/RECEIVE {'DUPLICATION ' if check_for_dupes else ''}TEST FAILED"
        )
        TEST_PASSED = False

    if check_for_no_proxy_id:
        proxy_pass = True
        print("Checking for no proxy ID")
        for message in received_messages_queue_acars:
            if "app" in message and "proxied" in message:
                print("Proxy ID found in ACARS message")
                TEST_PASSED = False
                proxy_pass = False
        for message in received_messages_queue_vdlm:
            if "proxied" in message["vdl2"]["app"]:
                print("Proxy ID found in VDLM message")
                TEST_PASSED = False
                proxy_pass = False

        if proxy_pass:
            print("Proxy ID check passed")
        else:
            print("Proxy ID check failed")
    else:
        proxy_pass = True
        print("Checking for proxy ID")
        for message in received_messages_queue_acars:
            if "app" not in message and "proxied" not in message:
                print("Proxy ID not found in ACARS message")
                TEST_PASSED = False
                proxy_pass = False
        for message in received_messages_queue_vdlm:
            if "proxied" not in message["vdl2"]["app"]:
                print("Proxy ID not found in VDLM message")
                TEST_PASSED = False
                proxy_pass = False

        if proxy_pass:
            print("Proxy ID check passed")
        else:
            print("Proxy ID check failed")

    if check_for_station_id:
        station_pass = True
        print("Checking for station ID")
        for message in received_messages_queue_acars:
            if "station_id" not in message:
                print("Station ID not found in ACARS message")
                TEST_PASSED = False
                station_pass = False
            elif message["station_id"] != check_for_station_id:
                print(
                    "Station ID does not match expected value in ACARS message. Found {}".format(
                        message["station_id"]
                    )
                )
                TEST_PASSED = False
                station_pass = False
        for message in received_messages_queue_vdlm:
            if "station" not in message["vdl2"]:
                print("Station ID not found in VDLM message")
                TEST_PASSED = False
                station_pass = False
            elif message["vdl2"]["station"] != check_for_station_id:
                print(
                    "Station ID does not match expected value in VDLM message. Found {}".format(
                        message["vdl2"]["station"]
                    )
                )
                TEST_PASSED = False
                station_pass = False

        if station_pass:
            print("Station ID check passed")
        else:
            print("Station ID check failed")

    if check_data_continuity:
        data_is_good = True
        print("Checking data continuity")
        for message in received_messages_queue_acars:
            if message not in test_messages:
                print("ACARS message not found in test messages")
                TEST_PASSED = False
                data_is_good = False
        for message in received_messages_queue_vdlm:
            if message not in test_messages:
                print("VDLM message not found in test messages")
                TEST_PASSED = False
                data_is_good = False

        if data_is_good:
            print("Data continuity check passed")
        else:
            print("Data continuity check failed")

    # Clean up

    print("Cleaning up sockets....standby")
    acars_sock.close()
    vdlm_sock.close()

    # stop all threads

    thread_stop_event.set()
    print("Done")
    sys.exit(0 if TEST_PASSED else 1)
