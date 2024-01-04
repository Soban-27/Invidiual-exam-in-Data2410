Simpleperf: 

This code creates a server and client, that works together on the same network.
When a client connects to the server, a new thread appears to handle the client.
When connected data will arrive and measure performance like transfer size, bandwidth speed, package loss, latency and more.
To conclude the script can be used to measure the network performance of network connection between two endpoints.


To run topology:

cd Documents
sudo -- custom mytopo.py topo mytopo

To run test case 1: 

Throughput 
Window 1: iperf -s -u 
Window 2: iperf -c 127.0.0.1 -u -b M

Test case 2: 

Latency: Ping 10.0.1.2 -c 25 >

Throughput 
Window 1: python3 simpleperf.py -s -b 10.0.1.2 (starting server)
Window 2: python3 simpleperf.py -c -I 10.0.1.2 -p 8088 -t 25  (starting client)

Test case 3: Is the same as 2 just remember to have the right host address as always.

Test case 4: Same as test case 2, but you have to run the test at the same time.

Test case 5: Same as the previous tests, just have -P 2 on h1 - h4

