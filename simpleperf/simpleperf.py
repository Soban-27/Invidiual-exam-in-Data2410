import argparse # Importing argparse for parser add arguments we are going to be directly following from guidelines
import socket # Importing socket module
import time # Importing time which will be useful for client.
import re
import threading
import sys
import queue


def parse_arguments():
    parser = argparse.ArgumentParser(description='Simpleperf') # Simpleperf
    parser.add_argument('-b', '--bind', type=str, default='127.0.0.1',
                        help=' -b or –bind : allows to select the ip address of the servers interface') #Binding the ip adress
    parser.add_argument('-p', '--server_port', type=int, default=8088,
                        help='-p or –port : port number on which the server should listen')
    parser.add_argument('-f', '--format', type=str, default='MB', choices=['B', 'KB', 'MB'],
                        help='–format: the format of the output data from [B, KB, MB') # Format
    server_or_client = parser.add_mutually_exclusive_group(required=True)
    server_or_client.add_argument('-s', '--server', action='store_true', help='Server mode') # The server
    server_or_client.add_argument('-c', '--client', action='store_true', help='Client mode') # The client
    parser.add_argument('-I', '--server_ip', type=str, default='127.0.0.1', help='IP')  #  selects the ip address of the server, default is localhost
    parser.add_argument('-t', '--total_time', '--time', type=int, default=25,
                        help='--time he total duration in seconds for which data should be generated') # Time where the default is 25
    parser.add_argument('-i', '--interval', type=int, help='Print statistics per z seconds', default=1.0)
    parser.add_argument('-P', '--parallel', type=int, default=1, choices=range(1, 6),
                        help='create parallel connections to connect to the server') #Useful in test case 5
    parser.add_argument("-n", "--num", dest="no_of_bytes", type=str, help="Number of bytes", default=0) #Should be in either in B, KB or MB
    return parser.parse_args() # Returning arguments


def parse_size(val):
    unit_type = {'B': 1, 'KB': 1000, 'MB': 1000000}
    # Check if the value matches the expected format
    if not re.match(r"^\d+[a-zA-Z]{1,2}$", val):
        raise ValueError(f"Invalid value: {val}")
    # Extract the numeral parts and unit part separately
    number, unit = int(val[:-2]), val[-2:].upper()
    # Look up the unit multiplier
    multiplier = unit_type.get(unit)
    if multiplier is None:
        raise ValueError(f"Invalid unit: {unit}")
    return number * multiplier


def server(args):
    with socket.socket() as server_socket:
        server_socket.bind((args.bind, args.server_port))
        server_socket.listen()         # Start listening for incoming connections

        print("-" * 60)
        # Print a message to indicate that the server is running and listening on the specified port
        print(f"A simpleperf server is listening on port {args.server_port}")
        print("-" * 60)

        while True:
            client_socket, client_address = server_socket.accept() # Wait for a client to connect and accept the connection

            # Print a message to indicate that a client has connected
            print("-" * 60)
            print(f"A simpleperf client with {client_address[0]}:{client_address[1]} is connected.")
            print("-" * 60)

            # Spawn a new thread to handle the client connection
            threading.Thread(target=handle_client, args=(client_socket, client_address, args)).start()


def handle_client(client_socket, client_address, args):
        buffer_size = 1000
        amount_of_bytes_received = 0
        start_time = time.time()

        while True:
            data = client_socket.recv(buffer_size)
            if not data or b'BYE' in data:
                break
            amount_of_bytes_received += len(data)

        end_time = time.time()
        total_duration = end_time - start_time

        unit_type = {'B': 1, 'KB': 1000, 'MB': 1000000}
        transfer_size = amount_of_bytes_received / unit_type[args.format]

        rate_server = (transfer_size * 8) / total_duration
        print(f"ID      Interval  Received    Rate")
        print(
            f"{client_address[0]}:{client_address[1]:<8} 0.0 - {int(total_duration):<10} {transfer_size:>10.0f} {args.format:<2} {rate_server:>10.2f} Mbps")

        try:
            client_socket.send(b"BYE")
        except OSError as e:
            print(f"Error sending data to client: {e}")
        finally:
            client_socket.close()


def client(args):
    def one_connection():

        # Creates socket in order to connect to server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((args.server_ip, args.server_port))
            client_address = client_socket.getsockname()

        print("Simpleperf client connecting to server {}, port {}".format(args.bind, args.server_port))

        start_time = time.time()  # Start time when client connects to server

        amount_of_bytes_sent = 0
        transfer_size = 0
        print("-" * 60)
        print("{:<25} {:<10} {:<15} {:<15}".format("ID", "Interval", "Transfer", "Bandwidth"))

        # Num (-n) flag
        # If the user specifies the size of data to be sent:
        if args.no_of_bytes:
            bytes_to_send = parse_size(args.no_of_bytes)
            while amount_of_bytes_sent < bytes_to_send:
                data = bytes(1000)  # send data in the chunks of 1000 bytes
                client_socket.sendall(data)
                amount_of_bytes_sent += len(data)

            transfer_size = amount_of_bytes_sent
            total_duration = time.time() - start_time
            rate_client = (transfer_size * 8) / total_duration
            print("-" * 60)
            print("{:<25} {:<10} {:<15} {:.2f} Mbps".format("{}:{}".format(client_address[0], client_address[1]),
                                                            "0-{:.1f}".format(int(total_duration)),
                                                            "{:.1f} MB".format(transfer_size / 1000000),
                                                            rate_client))

        else:
            # interval flag
            if args.interval:
                interval_start_time = start_time
                interval_bytes_sent = 0
                for i in range(int(args.interval), int(args.total_time) + int(args.interval), int(args.interval)):
                    # The loop will run until data is sent for the interval time.
                    while time.time() - interval_start_time <= args.interval:
                        data = bytes(1000)  # send data in the chunks of 1000 bytes
                        try:
                            client_socket.sendall(data)
                        except OSError as e:
                            print(f"Error sending data: {e}")
                            client_socket.close()
                            return
                        amount_of_bytes_sent += len(data)
                        interval_bytes_sent += len(data)

                    total_duration = time.time() - start_time
                    duration = args.interval
                    transfer_size += interval_bytes_sent
                    rate_client = (interval_bytes_sent * 8) / (duration * 1000000)
                    # print 0-5, 5-10, 10-15, 15-20, 20-25
                    # sending data at regular intervals takes place
                    print(
                        "{:<25} {:<10} {:<15} {:.2f} Mbps".format("{}:{}".format(client_address[0], client_address[1]),
                                                                  "{}-{}".format(i - args.interval, i),
                                                                  "{:.1f} MB".format(interval_bytes_sent / 1000000),
                                                                  rate_client))

                    interval_bytes_sent = 0
                    interval_start_time = time.time()

                rate_client = (transfer_size * 8) / total_duration
                print("-" * 60)
                print("{:<25} {:<10} {:<15} {:.2f} Mbps".format("{}:{}".format(client_address[0], client_address[1]),
                                                                "0-{:.1f}".format(int(total_duration)),
                                                                "{:.1f} MB".format(transfer_size / 1000000),
                                                                rate_client))



            else:

                # Calculate the number of iterations needed to cover the total time specified

                iterations = args.total_time // args.interval if args.interval else 1
                for i in range(iterations):

                    # Record the start time of the current interval and reset the bytes sent counter
                    interval_start_time = time.time()
                    interval_bytes_sent = 0

                    # Keep sending data until the current interval is over, or this is the first iteration

                    while time.time() - interval_start_time <= args.interval or i == 0:
                        data = bytes(1000)
                        client_socket.sendall(data)
                        amount_of_bytes_sent += len(data)
                        interval_bytes_sent += len(data)

                    # Calculate the duration of the interval and the sending rate achieved during that interval
                    duration = args.interval if args.interval else args.total_time
                    rate_client = (interval_bytes_sent * 8) / (duration * 1000000)

                    print(

                        "{:<25} {:<10} {:<15} {:.2f} Mbps".format(
                            "{}:{}".format(client_address[0], client_address[1]),
                            "{}-{}".format(i * args.interval, (i + 1) * args.interval - 1),
                            "{:.1f} MB".format(interval_bytes_sent / 1000000),
                            rate_client
                        )
                    )

    threads = []
    counter = queue.Queue()
    for _ in range(args.parallel):
        thread = threading.Thread(target=one_connection, args=())
        thread.start()
        threads.append(thread)
        time.sleep(1)
    for thread in threads:
        thread.join()


if __name__ == '__main__':
    args1 = parse_arguments()
    if args1.server:
        server(args1)
    elif args1.client:
        client(args1)
    else:
        print("Invalid arguments")

