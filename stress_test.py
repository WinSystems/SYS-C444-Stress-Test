# Author: Benjamin Herrera Navarro
# Date: 12/6/2023
# This code is licensed under the MIT License.

#            ______   ______     ____ _  _   _  _             
#           / ___\ \ / / ___|   / ___| || | | || |            
#           \___ \\ V /\___ \  | |   | || |_| || |_           
#            ___) || |  ___) | | |___|__   _|__   _|          
#  ____ ____|____/ |_|_|____/_ _\____| _|_|_ __|_| ____ _____ 
# / ___|_   _|  _ \| ____/ ___/ ___|  |_   _| ____/ ___|_   _|
# \___ \ | | | |_) |  _| \___ \___ \    | | |  _| \___ \ | |  
#  ___) || | |  _ <| |___ ___) |__) |   | | | |___ ___) || |  
# |____/ |_| |_| \_\_____|____/____/    |_| |_____|____/ |_|  
#This test was meant to stress test the SYS-C44 Hardware.

import sys
import time
import logging
from systemd.journal import JournalHandler
import os
import atexit
import spidev
import gpiod
import subprocess
import can
import threading
import time
import serial
import curses
import psutil
import  json 
from ctypes import cdll, c_char_p
from datetime import datetime

#Modify these to set default state of the test bruh 
test_status = {
    "TEMP0": {"status": "Not Started", "interval": 60000, "enabled": False},
    "TEMP1": {"status": "Not Started", "interval": 60000, "enabled": False},
    "SPI": {"status": "Not Started", "interval": 1000, "enabled": False},
    "GPIO": {"status": "Not Started", "interval": 1000, "enabled": True},
    #"CAN0": {"status": "Not Started", "interval": 1000, "enabled": True},
    #"CAN1": {"status": "Not Started", "interval": 1000, "enabled": True},
    "CAN": {"status": "Not Started", "interval": 1000, "enabled": True}, 
    "Memory": {"status": "Not Started", "interval": 1000, "enabled": False},
    "Ethernet0": {"status": "Not Started", "interval": 1000, "enabled": False},
    "Ethernet1": {"status": "Not Started", "interval": 1000, "enabled": False},
    "Wifi": {"status": "Not Started", "interval": 1000, "enabled": False},
    "UART": {"status": "Not Started", "interval": 1000, "enabled": True},
    "USB0": {"status": "Not Started", "interval": 1000, "enabled": False},
    "USB1": {"status": "Not Started", "interval": 1000, "enabled": False},
    "EMMC": {"status": "Not Started", "interval": 1000, "enabled": False},
    "SDCARD": {"status": "Not Started", "interval": 1000, "enabled": False},
    "JSON": {"status": "Not Started", "interval": 60000, "enabled": True}
}
# Global variables
spi_device = None
gpio_chip = None
exit_flag = False
last_update_time = 0
temperature = 0
temperature1 = 0
inodisk_c_lib = None
# Set up logging
log = logging.getLogger(__name__)
log.addHandler(JournalHandler())
log.setLevel(logging.INFO)
mypid = os.getpid()
log.info("SYSTEM-TEST: starting on pid " + str(mypid))

@atexit.register
def goodbye():
    global gpio_chip, spi_device

    log.info("SYSTEM-TEST: terminating")

    # # Close the gpiod chip if it's open
    # if gpio_chip is not None:
    #     try:
    #         gpiod.gpiod_chip_close(gpio_chip)
    #         log.info("GPIO chip successfully closed.")
    #     except Exception as e:
    #         log.error(f"Error closing GPIO chip: {e}")

    # Close the SPI device if it's open
    if spi_device is not None:
        try:
            spi_device.close()
            log.info("SPI device successfully closed.")
        except Exception as e:
            log.error(f"Error closing SPI device: {e}")

def dump_status_to_json(file_name="test_status.json"):
    log.info("SYSTEM-TEST: Starting JSON Thread")
    global exit_flag, test_status
    while not exit_flag:
        if test_status["JSON"]["enabled"]:
            test_status["JSON"]["status"] = "Running"
            interval = test_status["JSON"]["interval"] 
            try:
                new_data = {
                    "timestamp": datetime.now().isoformat(),
                    "status": test_status
                }
                data = []  # Default to an empty list if the file doesn't exist or is empty
                try:
                    # Read the existing data
                    with open(file_name, "r") as file:
                        data = json.load(file)
                        if not isinstance(data, list):
                            data = [data]  # Convert to list if it's not a list
                except (FileNotFoundError, json.JSONDecodeError):
                    pass  # Ignore file not found or JSON decode errors

                # Append the new data
                data.append(new_data)

                # Write the updated data back to the file
                with open(file_name, "w") as file:
                    json.dump(data, file, indent=4)

                # Sleep for user-defined time interval
                time.sleep(interval / 1000.0)

            except Exception as e:
                log.error(f"SYSTEM-TEST: JSON Logging Error: {e}")

        else:
            test_status["JSON"]["status"] = "Idle"
            time.sleep(1)
    log.info("SYSTEM-TEST: Closing JSON Thread")


def log_temperature0():
    log.info("SYSTEM-TEST: Starting Temperature Logging Thread 0")
    global exit_flag, test_status, temperature
    while not exit_flag:
        interval = test_status["TEMP0"]["interval"] 
        if test_status["TEMP0"]["enabled"]:
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as temp_file, \
                     open('/proc/uptime', 'r') as uptime_file:

                    test_status["TEMP0"]["status"] = "Running"
                    temperature = int(temp_file.read()) / 1000.0  # Convert to Celsius
                    uptime_seconds = float(uptime_file.read().split()[0])  # Uptime in seconds
                    log.info(f"Uptime: {uptime_seconds:.2f} seconds, Temperature: {temperature} °C")
                    #if test_status["TEMP0"]["enabled"]:
                    time.sleep(interval/1000.0)

            except Exception as e:
                log.error(f"Temperature test failed: {e}")
                test_status["TEMP0"]["status"] = "Failed"
        else:
            test_status["TEMP0"]["status"] = "Idle"
            time.sleep(1)

    log.info("SYSTEM-TEST: Closing Temperature Logging Thread 0")

def log_temperature1():
    log.info("SYSTEM-TEST: Starting Temperature Logging Thread 1")
    global exit_flag, test_status, temperature1
    while not exit_flag:
        interval = test_status["TEMP1"]["interval"] 
        if test_status["TEMP1"]["enabled"]:
            try:
                with open('/sys/class/thermal/thermal_zone1/temp', 'r') as temp_file, \
                     open('/proc/uptime', 'r') as uptime_file:

                    test_status["TEMP1"]["status"] = "Running"
                    temperature1 = int(temp_file.read()) / 1000.0  # Convert to Celsius
                    uptime_seconds = float(uptime_file.read().split()[0])  # Uptime in seconds
                    log.info(f"Uptime: {uptime_seconds:.2f} seconds, Temperature: {temperature1} °C")
                    #if test_status["TEMP1"]["enabled"]:
                    time.sleep(interval/1000.0)

            except Exception as e:
                log.error(f"Temperature test failed: {e}")
                test_status["TEMP1"]["status"] = "Failed"
        else:
            test_status["TEMP1"]["status"] = "Idle"
            time.sleep(1)

    log.info("SYSTEM-TEST: Closing Temperature Logging Thread 1")



def run_spi_stress_test():
    log.info("SYSTEM-TEST: Starting SPI Thread")
    global exit_flag, test_status, spi_device
    while not exit_flag:
        if test_status["SPI"]["enabled"]:
            try:
                #Open SPIDEV device
                spi_device = spidev.SpiDev()
                spi_device.open(0, 0)
                test_status["SPI"]["status"] = "Running"
                count = 0
                while test_status["SPI"]["enabled"]:
                    #Assign sleep interval
                    spi_write_interval = test_status["SPI"]["interval"]
                    count += 1
                    resp = spi_device.xfer2([(count & 0xff)])  # Transfer one byte
                    #if test_status["SPI"]["enabled"]:
                    time.sleep(spi_write_interval/1000.0)
                    # if not(count % 20000):
                    log.info("SPI count=" + str(count))
                        # os.system('/bin/journalctl --flush')
                    test_status["SPI"]["status"] = "Running"
            #Catch exemption
            except Exception as e:
                log.error(f"SPI test failed: {e}")
                test_status["SPI"]["status"] = "Failed"
        else:
            test_status["SPI"]["status"] = "Idle"
            time.sleep(1)

    log.info("SYSTEM-TEST: Closing SPI Thread")
    # If exit loop attempt to close device
    # Close the SPI device if it's open
    # if spi_dev is not None:
    #     try:
    #         spi_dev.close()
    #         log.info("SPI device successfully closed.")
    #     except Exception as e:
    #         log.error(f"Error closing SPI device: {e}")


def run_gpio_stress_test(gpio_toggle_interval):
    chip = gpiod.chip('gpiochip0')
    gpios = [chip.get_line(i) for i in [0, 1, 3, 5, 6, 7]]

    config_output = gpiod.line_request()
    config_output.consumer = "GPIOD TEST 1"
    config_output.request_type = gpiod.line_request.DIRECTION_OUTPUT

    for gpio in gpios:
        gpio.request(config_output, 0)

    count = 0
    while True:
        count += 1
        for gpio in gpios:
            gpio.set_value(1)
        time.sleep(gpio_toggle_interval)

        for gpio in gpios:
            gpio.set_value(0)
        time.sleep(gpio_toggle_interval)

        if not(count % 5000):
            log.info("GPIO count=" + str(count))
            os.system('/bin/journalctl --flush')


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def run_gpio_loopback_test():
    log.info("SYSTEM-TEST: Starting GPIO Loopback Test")
    global exit_flag, gpio_chip, test_status

    gpio0 = None
    gpio1 = None
    gpio2 = None
    gpio3 = None
    gpio4 = None
    gpio5 = None
    
    while not exit_flag:
        if test_status["GPIO"]["enabled"]:
            try:
                test_status["GPIO"]["status"] = "Running"
                test_failed = False
                # Get GPIO0 Bank/gpiochip0
                chip=gpiod.chip('gpiochip0')

                # Get gpiochip0 bank lines
                gpio0 = chip.get_line(0)
                gpio1 = chip.get_line(1)
                gpio2 = chip.get_line(3)
                gpio3 = chip.get_line(5)
                gpio4 = chip.get_line(6)
                gpio5 = chip.get_line(7)

                # Create Output config
                config_output = gpiod.line_request()
                config_output.consumer = "GPIO TEST 1"
                config_output.request_type = gpiod.line_request.DIRECTION_OUTPUT

                # Create Input config
                config_input = gpiod.line_request()
                config_input.consumer = "GPIO TEST 2"
                config_input.request_type = gpiod.line_request.DIRECTION_INPUT

                # Request GPIO to kernel
                gpio0.request(config_output, 0)
                gpio1.request(config_output, 0)
                gpio2.request(config_output, 0)
                gpio3.request(config_input, 0)
                gpio4.request(config_input, 0)
                gpio5.request(config_input, 0)
                # Loopback test
                while test_status["GPIO"]["enabled"]:
                    # Create loopback pairs
                    loopback_pairs = [
                        [[gpio0, 'gpio0'], [gpio3, 'gpio3']],
                        [[gpio1, 'gpio1'], [gpio4, 'gpio4']],
                        [[gpio2, 'gpio2'], [gpio5, 'gpio5']],
                    ]
                    test_failed = False

                    okay_str = (bcolors.OKGREEN + 'Okay' + bcolors.ENDC)
                    fail_str = (bcolors.FAIL + 'Fail' + bcolors.ENDC)
                    log.info("Testing GPIO[0, 1, 2] WRITE | GPIO[3, 4, 5] READ")
                    for pair in loopback_pairs:
                        # log.info("Set {0} OUTPUT | Set {1} INPUT".format(pair[0][1], pair[1][1]))
                        # Set first pair as output
                        pair[0][0].set_direction_output()
                        # Set second pair as input
                        pair[1][0].set_direction_input()

                    for pair in loopback_pairs:
                        pair[0][0].set_value(1)
                        if (pair[1][0].get_value()!=1):
                            log.info("TEST {0}: WRITE 1 | {1}: READ | STATUS: {2}".format(pair[0][1], pair[1][1],
                                (okay_str) if (pair[1][0].get_value()==1) else "{0} {1}".format(fail_str, pair[1][0].get_value())))
                            test_failed = True

                        pair[0][0].set_value(0)
                        if (pair[1][0].get_value()!=0):
                            log.info("TEST {0}: WRITE 0 | {1}: READ | STATUS: {2}".format(pair[0][1], pair[1][1],
                            (okay_str) if (pair[1][0].get_value()==0) else "{0} {1}".format(fail_str, pair[1][0].get_value())))
                            test_failed = True

                    log.info("Testing GPIO[0, 1, 2] READ | GPIO[3, 4, 5] WRITE")
                    for pair in loopback_pairs:
                        # log.info("Set {0} OUTPUT | Set {1} INPUT".format(pair[0][1], pair[1][1]))
                        #Set first pair as input
                        pair[0][0].set_direction_input()
                        #Set second pair as output
                        pair[1][0].set_direction_output()

                    for pair in loopback_pairs:
                        pair[1][0].set_value(1)
                        if (pair[1][0].get_value()!=1):
                            log.info("TEST {0}: WRITE 1 | {1}: READ | STATUS: {2}".format(pair[1][1], pair[0][1],
                                (okay_str) if (pair[0][0].get_value()==1) else "{0} {1}".format(fail_str, pair[1][0].get_value())))
                            test_failed = True
                        pair[1][0].set_value(0)
                        if (pair[1][0].get_value()!=0):
                            log.info("TEST {0}: WRITE 0 | {1}: READ | STATUS: {2}".format(pair[1][1], pair[0][1],
                                (okay_str) if (pair[0][0].get_value()==0) else "{0} {1}".format(fail_str, pair[0][0].get_value())))
                            test_failed = True                
                    # Delay between test cycles
                    gpio_toggle_interval = test_status["GPIO"]["interval"]
                    #if test_status["GPIO"]["enabled"]:
                    time.sleep(gpio_toggle_interval/1000.0)
                    if test_failed:
                        test_status["GPIO"]["status"] = "Failed"
                    else:
                        test_status["GPIO"]["status"] = "Running"

            except Exception as e:
                log.error(f"GPIO Loopback test failed: {e}")
                test_status["GPIO"]["status"] = "Failed"
            finally:
                # Release lines
                if gpio0 is not None: gpio0.release()
                if gpio1 is not None: gpio1.release()
                if gpio2 is not None: gpio2.release()
                if gpio3 is not None: gpio3.release()
                if gpio4 is not None: gpio4.release()
                if gpio5 is not None: gpio5.release()
                # gpio_chip.close()
        else:
            test_status["GPIO"]["status"] = "Idle"
            time.sleep(1)  # Check the status in intervals when disabled

    log.info("SYSTEM-TEST: Closing GPIO Thread")
    # Close the gpiod chip if it's open
    if gpio_chip is not None:
        try:
            # Release lines
            if gpio0 is not None: gpio0.release()
            if gpio1 is not None: gpio1.release()
            if gpio2 is not None: gpio2.release()
            if gpio3 is not None: gpio3.release()
            if gpio4 is not None: gpio4.release()
            if gpio5 is not None: gpio5.release()
            log.info("GPIO chip successfully closed.")
        except Exception as e:
            log.error(f"Error closing GPIO chip: {e}")

def write_and_verify_device(device_path, test_name):
    log.info(f"Starting Write and Verify test thread for device {device_path}")
    global exit_flag, test_status
    test_data = bytearray([0xde, 0xad, 0xbe, 0xef])
    while not exit_flag:
        if test_status[test_name]["enabled"]:
            try:
                # Open the device for writing and reading in binary mode
                with open(device_path, 'wb+') as device:
                    log.info(f"Writing to device {device_path}")
                    device.write(test_data)
                    device.flush()  # Ensure data is written to the device

                    # Go back to the start of the device
                    device.seek(0)

                    # Read back the data for verification
                    read_data = device.read(len(test_data))
                    if read_data != test_data:
                        log.info(f"Write and Verify test: {device_path} read data did not match")
                        test_status[test_name]["status"] = "Failed"
                        raise IOError("Verification failed: Read data does not match written data")
                    else:
                        test_status[test_name]["status"] = "Running"
                        log.info(f"Successfully wrote and verified data on {device_path}")

                # Wait for the specified interval before the next write
                #if test_status[test_name]["enabled"]:
                time.sleep(test_status[test_name]["interval"]/1000.0)

            except Exception as e:
                test_status[test_name]["status"] = "Failed"
                log.error(f"Write and Verify Test: Error occurred with device {device_path}: {e}")
                # break  # Exit the loop if an error occurs
        else:
            test_status[test_name]["status"] = "Idle"
            time.sleep(1)

    log.info(f"Exit Write and Verify test thread for device {device_path}")


def setup_can_devices(socket_name_1='emuccan0', socket_name_2='emuccan1'):
    try:
        # Run the emucd_64 command
        #emucd_64 -s7 -e0 ttyACM0 emuccan0 emuccan1
        subprocess.run(['emucd_64', '-s7', '-e0', 'ttyACM0', socket_name_1, socket_name_2], check=True)
        log.info("CAN devices setup successfully.")

        # Configure CAN devices txqueuelen
        subprocess.run(['ip', 'link', 'set', socket_name_1, 'txqueuelen', '1000'], check=True)
        subprocess.run(['ip', 'link', 'set', socket_name_2, 'txqueuelen', '1000'], check=True)
        log.info("Configured CAN devices txqueuelen to 1000.")

        # # Setup Traffic Control (tc) queuing discipline
        # subprocess.run(['tc', 'qdisc', 'add', 'dev', socket_name_1, 'root', 'handle', '1:', 'pfifo'], check=True)
        # subprocess.run(['tc', 'qdisc', 'add', 'dev', socket_name_2, 'root', 'handle', '1:', 'pfifo'], check=True)
        # print("Set up tc queuing discipline.")

        # Bring up the CAN interfaces
        subprocess.run(['ip', 'link', 'set', 'dev', socket_name_1, 'up'], check=True)
        subprocess.run(['ip', 'link', 'set', 'dev', socket_name_2, 'up'], check=True)
        log.info(f"{socket_name_1} and {socket_name_2} are up.")

    except subprocess.CalledProcessError as e:
        log.info(f"An error occurred: {e}")
    except FileNotFoundError:
        log.info("Command not found. Please ensure it's installed and in your PATH.")

# def send_can_message(interface, message):
#     bus = can.interface.Bus(channel=interface, bustype='socketcan')
#     msg = can.Message(arbitration_id=0x123, data=message, is_extended_id=False)
#     try:
#         bus.send(msg)
#         print(f"Message sent on {interface}")
#     except can.CanError:
#         print(f"Message failed to send on {interface}")

# def receive_can_message(interface, expected_message):
#     bus = can.interface.Bus(channel=interface, bustype='socketcan')
#     while True:
#         msg = bus.recv()  # Blocking call, will wait for a message
#         if msg is not None:
#             print(f"Message received on {interface}: {msg.data}")
#             if msg.data == expected_message:
#                 print("Received message matches expected message.")
#                 break

# def run_socket_can_test():
#     test_message = [0x01, 0x02, 0x03, 0x04]  # Example data
#     test_delay = 1  # Delay between tests in seconds

#     while True:
#         stop_event = threading.Event()
#         receiver_thread = threading.Thread(target=receive_can_message, args=('emuccan1', test_message, stop_event))
#         receiver_thread.start()

#         time.sleep(1)  # Give a moment for the receiver to start

#         send_can_message('emuccan0', test_message)

#         receiver_thread.join(timeout=5)
#         stop_event.set()

#         if receiver_thread.is_alive():
#             log.warning("Receiver thread did not finish, terminating now.")
#             receiver_thread.join()

#         time.sleep(test_delay)  # Delay between tests

def send_and_receive_can_message(bus, can_id, message, timeout=10):
    """Send a CAN message and wait for its reception."""
    try:
        # Send the message
        msg = can.Message(arbitration_id=can_id, data=message, is_extended_id=False)
        bus.send(msg)
        logging.info(f"Sent message: {msg}")

        # Wait for reception
        start_time = time.time()
        while time.time() - start_time < timeout:
            received_msg = bus.recv(1.0)  # Timeout in seconds
            if received_msg:
                logging.info(f"Received message: {received_msg}")
                if received_msg.arbitration_id == can_id and received_msg.data == message:
                    logging.info("Loopback successful: Received expected message")
                    return
                else:
                    logging.warning("Received unexpected message")
            else:
                logging.warning("No message received within the interval")
                break

    except can.CanError as e:
        logging.error(f"CAN communication error: {e}")

def run_can_loopback_test(interface_name, can_id, message):
    # Setup CAN bus in loopback mode
    bus = can.interface.Bus(interface_name, bustype='socketcan', receive_own_messages=True)

    # Run the send and receive test
    send_and_receive_can_message(bus, can_id, message)

    # Cleanup
    bus.shutdown()

def run_inodisk_can_loopback_test():
    try:
        log.info(f"Starting INODISK loopback thread for.")
        global exit_flag, test_status
        while not exit_flag:
            if test_status[test_name]["enabled"]:


                    result = subprocess.run(['ping', '-I', interface, '-c', '1', destination], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if result.returncode == 0:
                        log.info(f"{interface}: Ping successful")
                        test_status[test_name]["status"] = "Running"
                    else:
                        log.error(f"{interface}: Ping failed with return code {result.returncode}")
                        test_status[test_name]["status"] = "Failed"
                    time.sleep(test_status[test_name]["interval"]/1000.0)
            else:
                test_status[test_name]["status"] = "Idle"
                time.sleep(1)

    except Exception as e:
        log.error(f"Error INODISK loopback test: {e}")
    log.info(f"Stopping INODISK loopback test")



def ping_from_interface(interface, test_name, destination="8.8.8.8"):
    try:
        log.info(f"Starting ETHERNET pinging thread for {interface}")
        global exit_flag, test_status
        while not exit_flag:
            if test_status[test_name]["enabled"]:
                    result = subprocess.run(['ping', '-I', interface, '-c', '1', destination], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if result.returncode == 0:
                        log.info(f"{interface}: Ping successful")
                        test_status[test_name]["status"] = "Running"
                    else:
                        log.error(f"{interface}: Ping failed with return code {result.returncode}")
                        test_status[test_name]["status"] = "Failed"
                    time.sleep(test_status[test_name]["interval"]/1000.0)
            else:
                test_status[test_name]["status"] = "Idle"
                time.sleep(1)
    except Exception as e:
        log.error(f"Error pinging from {interface}: {e}")
    log.info(f"Stopping ETHERNET pinging thread for {interface}")

def run_memory_stress_test(stress_duration=10):  # Duration in seconds
    global test_status, exit_flag
    while not exit_flag:
        if test_status["Memory"]["enabled"]:
            try:
                test_status["Memory"]["status"] = "Running"
                try:
                    # Stress 1GB of memory for the specified duration
                    subprocess.run(['stress-ng', '--vm', '1', '--vm-bytes', '1G', '--timeout', str(stress_duration)], check=True)
                    log.info("Memory stress test completed successfully.")
                except subprocess.CalledProcessError as e:
                    log.error(f"Memory stress test failed: {e}")
                except FileNotFoundError:
                    log.error("stress-ng command not found. Please ensure it's installed and in your PATH.")
                test_status["Memory Stress"] = "Successful"
            except Exception as e:
                log.error(f"Memory Stress test failed: {e}")
                test_status["Memory"]["status"] = "Failed"
        else:
            test_status["Memory"]["status"] = "Idle"
            time.sleep(1)


def ethernet_loopback_test(ip_eth1, port, message, test_duration):
    received_messages = []
    send_count = 0

    def receiver():
        nonlocal received_messages
        with subprocess.Popen(['nc', '-l', '-p', str(port)], stdout=subprocess.PIPE, text=True) as process:
            start_time = time.time()
            while time.time() - start_time < test_duration:
                data = process.stdout.readline().strip()
                if data:
                    received_messages.append(data)

    def sender():
        start_time = time.time()
        while time.time() - start_time < test_duration:
            try:
                subprocess.run(f'echo "{message}" | nc {ip_eth1} {port}', shell=True, check=True)
                send_count += 1
            except subprocess.CalledProcessError:
                log.error("Ethernet loopback send: Failed to send data.")
            time.sleep(1)  # Sending interval

    receiver_thread = threading.Thread(target=receiver)
    sender_thread = threading.Thread(target=sender)

    receiver_thread.start()
    sender_thread.start()

    receiver_thread.join()
    sender_thread.join()

    # Test result based on message count
    if len(received_messages) == send_count:
        log.info(f"Ethernet loopback test passed. {len(received_messages)} messages received.")
        return True
    else:
        log.error(f"Ethernet loopback test failed. {len(received_messages)} of {send_count} messages received.")
        return False

def continuous_ethernet_loopback_testing(ip_eth1, port, message, test_duration, max_iterations=None):
    iteration = 0
    while True:
        iteration += 1
        log.info(f"Starting Ethernet loopback test iteration {iteration}")
        
        test_passed = ethernet_loopback_test(ip_eth1, port, message, test_duration)
        
        if not test_passed:
            log.error(f"Ethernet loopback test failed on iteration {iteration}")
            break  # Stop the loop if the test fails

        if max_iterations and iteration >= max_iterations:
            log.info("Reached the maximum number of iterations for Ethernet loopback testing.")
            break  # Stop after reaching the maximum number of iterations

        # Optional: Add a delay between iterations
        time.sleep(1)  # Delay of 1 second between tests

    log.info("Completed continuous Ethernet loopback testing.")


def can_bus_test_inodisk():
    """
    This function will use the InoDisk CAN BUS loopback functions written in C.
    
    """
    log.info("SYSTEM-TEST: Starting CAN TEST Thread")     
    global test_status, exit_flag
    timeout = 5.0
    log.info("SYSTEM-TEST: CAN BUS on Stand By")     
    msg_err = None
    test_status["CAN"]["status"] = "Running"
    #Open Ini file
    ret = inodisk_c_lib.open_init()
    if ret:
        log.info("SYSTEM-TEST: Failed to open .ini configuration file.")
        #We disable CAN testing because .ini file was not found
        test_status["CAN"]["enabled"] = False
        test_status["CAN"]["status"] = "Failed"
        return
    else:
        log.info("SYSTEM-TEST: Sucessfully opened .ini configuration file.")

    while not exit_flag:
        #Check if the test is enabled
        if test_status["CAN"]["enabled"]:
            
             loopback_status = False
             try:
    #             msg = bus.recv(timeout=2)  # Receive a message
    #             msg_err = msg
    #             if msg is not None:
    #                 # Check if 'TEST' is in the message data
    #                 if 'TEST' in msg.data.decode('utf-8', errors='ignore'):
    #                     log.info(f"CAN: Recieved: {msg}")
    #                     found_test = True
    #                     # Wait for the specified interval before reading the next message
    #                     test_status[test_name]["status"] = "Running"
    #                 else:
    #                     log.error(f"CAN: Wrong Data {msg}")
                ret = inodisk_c_lib.start_testing()
                if not ret:
                    test_status["CAN"]["status"] = "Running"
                else:
                    test_status["CAN"]["status"] = "Failed"


             except Exception as e:
                 log.error(f"SYSTEM-TEST: CAN TEST Error: {e}")
                 time.sleep(0.1)


             time.sleep(test_status["CAN"]["interval"]/1000.0)
         else:
             #Test on Idle
             test_status["CAN"]["status"] = "Idle"
             time.sleep(1)

    log.info("SYSTEM-TEST: Closing CAN TEST Thread")
     
    except Exception as e:
        log.info(f"SYSTEM-TEST: CAN Test Error: {e}")

def setup_serial_port():
    if os.geteuid() != 0:
        log.info("This function needs to be run as root.")
        return

    commands = ["dmesg -D", "systemctl stop serial-getty@ttymxc0"]

    for command in commands:
        try:
            subprocess.run(command, shell=True, check=True)
            log.info(f"Successfully executed: {command}")
        except subprocess.CalledProcessError as e:
            log.info(f"An error occurred while executing {command}: {e}")

    log.info("Serial port setup completed.")

def uart_loopback_test(send_port="/dev/ttymxc0", receive_port="/dev/ttymxc1", baud_rate=115200, test_message="TEST"):
    log.info("SYSTEM-TEST: Starting UART Loopback Thread")
    setup_serial_port()
    # Shared variable to store the result of the receive function
    receive_result = {"success": False}

    # Open both ports
    ser_send = serial.Serial(send_port, baud_rate, timeout=1)
    ser_receive = serial.Serial(receive_port, baud_rate, timeout=1)

    def send():
        ser_send.write(test_message.encode())
        log.info(f"Sent '{test_message}' on {send_port}")

    def receive():
        time.sleep(1)  # Wait a bit to ensure data is sent
        data = ser_receive.read(len(test_message))
        received_message = data.decode()
        if received_message == test_message:
            log.info(f"Received '{received_message}' on {receive_port} - Loopback Successful")
            receive_result["success"] = True
        else:
            log.error(f"Received incorrect data on {receive_port} - Loopback Failed")
            log.error(f"Received Data: {received_message}")
            receive_result["success"] = False

    global exit_flag, test_status

    while not exit_flag:
        if test_status["UART"]["enabled"]:
            try:
                send()
                receive()

                # Check the result of the receive thread
                if receive_result["success"]:
                    test_status["UART"]["status"] = "Running"
                else:
                    test_status["UART"]["status"] = "Failed"

            except Exception as e:
                test_status["UART"]["status"] = "Failed"
                log.error(f"UART Loopback test failed: {e}")
        else:
            test_status["UART"]["status"] = "Idle"
        
        # Sleep to set test interval
        time.sleep(test_status["UART"]["interval"] / 1000.0)

    log.info("SYSTEM-TEST: Closing UART Loopback Thread")

# Test status and interval dictionary

def init_colors():
    curses.start_color()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)

# Shared variable for the selected row
selected_row_idx = 0

def draw_menu(stdscr):
    global selected_row_idx, exit_flag, temperature, last_update_time
    init_colors()

    while not exit_flag:
        handle_input(stdscr)
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        # Get and display CPU and Memory usage
        current_time = time.time()

        # Check if one second has passed to update CPU and Memory usage
        if current_time - last_update_time >= 1:
            cpu_usage = psutil.cpu_percent()
            mem_usage = psutil.virtual_memory().percent
            last_update_time = current_time

        stdscr.addstr(1, w//2 - len(f"CPU: {cpu_usage}% MEM: {mem_usage}% TEMP0: {temperature}C TEMP1: {temperature1}C")//2,
                    f"CPU: {cpu_usage}% MEM: {mem_usage}% TEMP0: {temperature}C TEMP1: {temperature1}C")

        # Draw the table
        for idx, test in enumerate(test_status):
            x = w//2 - 30  # Adjust starting position
            y = h//2 - len(test_status)//2 + idx + 1

            # Determine the enabled status
            enabled_status = "Enabled" if test_status[test]["enabled"] else "Disabled"
            status_color = curses.color_pair(2) if test_status[test]["enabled"] else curses.color_pair(1)

            # Highlight the selected row
            if idx == selected_row_idx:
                stdscr.attron(curses.A_REVERSE)

            # Display test name with enabled/disabled status
            stdscr.addstr(y, x, f"{test.ljust(15)} [{enabled_status}]".ljust(30))
            stdscr.attroff(curses.A_REVERSE)  # Turn off highlight

            # Display status and interval
            status = test_status[test]["status"]
            interval = test_status[test]["interval"]
            stdscr.addstr(y, x + 30, f"{status}".ljust(20) + f"{interval}ms", status_color)

        stdscr.refresh()
        time.sleep(0.01)

def create_input_window(stdscr):
    h, w = stdscr.getmaxyx()
    input_win = curses.newwin(3, w-2, h-3, 1)
    stdscr.refresh()
    return input_win

def handle_input(stdscr):
    global selected_row_idx, exit_flag, test_status
    input_win = create_input_window(stdscr)

    stdscr.nodelay(True)  # Set stdscr to non-blocking mode
    # while not exit_flag:
    key = stdscr.getch()

    if key == curses.KEY_UP and selected_row_idx > 0:
        selected_row_idx -= 1
    elif key == curses.KEY_DOWN and selected_row_idx < len(test_status) - 1:
        selected_row_idx += 1
    elif key == ord('+'):
        test_status[list(test_status)[selected_row_idx]]["interval"] += 10
    elif key == ord('-') and test_status[list(test_status)[selected_row_idx]]["interval"] > 10:
        test_status[list(test_status)[selected_row_idx]]["interval"] -= 10
    elif key == ord('e'):  # Enable the selected test
        test_status[list(test_status)[selected_row_idx]]["enabled"] = True
    elif key == ord('d'):  # Disable the selected test
        test_status[list(test_status)[selected_row_idx]]["enabled"] = False
    elif key == ord('q'):
        exit_flag = True
        test_status = {
                "TEMP0": {"status": "Closing Down", "interval": 60000, "enabled": False},
                "TEMP1": {"status": "Closing Down", "interval": 60000, "enabled": False},
                "SPI": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "GPIO": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "CAN": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "Memory": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "Ethernet0": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "Ethernet1": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "Wifi": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "UART": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "USB0": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "USB1": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "EMMC": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "SDCARD": {"status": "Closing Down", "interval": 1000, "enabled": False},
                "JSON": {"status": "Closing Down", "interval": 1000, "enabled": False}
            }
    elif key == ord('r'):
        exit_flag = False
        test_status = {
                "TEMP0": {"status": "State Reset", "interval": 60000, "enabled": False},
                "TEMP1": {"status": "State Reset", "interval": 60000, "enabled": False},
                "SPI": {"status": "State Reset", "interval": 1000, "enabled": False},
                "GPIO": {"status": "State Reset", "interval": 1000, "enabled": False},
                "CAN": {"status": "State Reset", "interval": 1000, "enabled": False},
                "Memory": {"status": "State Reset", "interval": 1000, "enabled": False},
                "Ethernet0": {"status": "State Reset", "interval": 1000, "enabled": False},
                "Ethernet1": {"status": "State Reset", "interval": 1000, "enabled": False},
                "Wifi": {"status": "State Reset", "interval": 1000, "enabled": False},
                "UART": {"status": "State Reset", "interval": 1000, "enabled": False},
                "USB0": {"status": "State Reset", "interval": 1000, "enabled": False},
                "USB1": {"status": "State Reset", "interval": 1000, "enabled": False},
                "EMMC": {"status": "State Reset", "interval": 1000, "enabled": False},
                "SDCARD": {"status": "State Reset", "interval": 1000, "enabled": False},
                "JSON": {"status": "State Reset", "interval": 1000, "enabled": False}
            }
        stdscr.clear()
    elif key != -1:  # Any other key
        handle_additional_input(input_win, key)

def handle_additional_input(input_win, key):
    # Handle additional inputs here, e.g., text input
    pass

def run_curses(stdscr):
    inodisk_c_lib = cdll.LoadLibrary("./Loopback_EMUC2/loopback.so")
    # stdscr.curs_set(0)

    log.info("SYSTEM-TEST: CAN: Setting up devices")
    # setup_can_devices("can0", "can1")

    draw_thread = threading.Thread(target=draw_menu, args=(stdscr,))
    # input_thread = threading.Thread(target=handle_input, args=(stdscr,))
    temperature_thread0 = threading.Thread(target=log_temperature0)
    temperature_thread1 = threading.Thread(target=log_temperature1)
    spi_thread = threading.Thread(target=run_spi_stress_test)
    gpio_thread = threading.Thread(target=run_gpio_loopback_test)
    memory_thread = threading.Thread(target=run_memory_stress_test)
    uart_thread = threading.Thread(target=uart_loopback_test)
    usb0_thread = threading.Thread(target=write_and_verify_device, args=("/dev/sda", "USB0"))
    usb1_thread = threading.Thread(target=write_and_verify_device, args=("/dev/sdb", "USB1"))
    emmc_thread = threading.Thread(target=write_and_verify_device, args=("/dev/emmcblk0", "EMMC"))
    sdcard_thread = threading.Thread(target=write_and_verify_device, args=("/dev/emmcblk1", "SDCARD"))
    ethernet0_thread = threading.Thread(target=ping_from_interface, args=("eth0", "Ethernet0"))
    ethernet1_thread = threading.Thread(target=ping_from_interface, args=("eth1", "Ethernet1"))
    wifi_thread = threading.Thread(target=ping_from_interface, args=("wlan0", "Wifi"))
    json_thread = threading.Thread(target=dump_status_to_json)
    can_thread = threading.Thread(target=can_bus_test_inodisk)
    #can0_thread = threading.Thread(target=can_bus_test, args=("CAN0", "can0"))
    #can1_thread = threading.Thread(target=can_bus_test, args=("CAN1", "can1"))


    draw_thread.start()
    # input_thread.start()
    temperature_thread0.start()
    temperature_thread1.start()
    spi_thread.start()
    gpio_thread.start()
    memory_thread.start()
    uart_thread.start()
    usb0_thread.start()
    usb1_thread.start()
    emmc_thread.start()
    sdcard_thread.start()
    ethernet0_thread.start()
    ethernet1_thread.start()
    wifi_thread.start()
    json_thread.start()
    #can0_thread.start()
    #can1_thread.start()
    can_thread.start()
    
    draw_thread.join()
    # input_thread.join()
    temperature_thread0.join()
    temperature_thread1.join()
    spi_thread.join()
    gpio_thread.join()
    memory_thread.join()
    uart_thread.join()
    usb0_thread.join()
    usb1_thread.join()
    emmc_thread.join()
    # sdcard_thread.join()
    ethernet0_thread.join()
    ethernet1_thread.join()
    wifi_thread.join()
    json_thread.join()
    #can0_thread.join()
    #can1_thread.join()
    can_thread.join()

def main():
    # curses.curs_set(0)
    curses.wrapper(run_curses)


if __name__ == "__main__":
    main()

