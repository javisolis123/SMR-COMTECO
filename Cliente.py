#!/usr/bin/python3
import socket
import select
import errno
import Adafruit_DHT
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time
import errno
from socket import error as socket_error

HEADER_LENGTH = 10
aux = True
IP = "192.168.10.20"
PORT = 1235
my_username = "Tuti"

# Creación del Socket
# socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
# socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Conexión otorgando una IP y un Puerto
while aux:
    try:
        client_socket.connect((IP, PORT))
        break
    except socket_error as serr:
        pass
    

# Set connection to non-blocking state, so .recv() call won;t block, just return some exception we'll handle
client_socket.setblocking(False)

# Prepare username and header and send them
# We need to encode username to bytes, then count number of bytes and prepare header of fixed size, that we encode to bytes as well
username = my_username.encode('utf-8')
username_header = f"{len(username):<{HEADER_LENGTH}}".encode('utf-8')
client_socket.send(username_header + username)


#################Configuracion del sensor de Humedad y temperatura#################
sensor = Adafruit_DHT.DHT11
pin = 23



#################Configuracion del conversor analogo digital#################

# Create the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADS object
#ads = ADS.ADS1015(i2c)
ads = ADS.ADS1115(i2c)

# Create a sinlge ended channel on Pin 0
#   Max counts for ADS1015 = 2047
#                  ADS1115 = 32767
chan = AnalogIn(ads, ADS.P0)
chan1 = AnalogIn(ads,ADS.P1)

# The ADS1015 and ADS1115 both have the same gain options.
#
#       GAIN    RANGE (V)
#       ----    ---------
#        2/3    +/- 6.144
#          1    +/- 4.096
#          2    +/- 2.048
#          4    +/- 1.024
#          8    +/- 0.512
#         16    +/- 0.256
#
gains = (2/3, 1, 2, 4, 8, 16)
ads.gain = gains[0]
while True:
    time.sleep(1)
    message = "NONE"
    # Lectura de Temperatura y Humedad
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
    if humidity is not None and temperature is not None:
            message = str(temperature) + "," + str(humidity) + "," + str(chan.voltage) + "," + str(chan1.voltage) + "," + time.strftime("%H:%M:%S")
    else:
            message = '1000' + "," + '1000' + "," + str(chan.voltage) + "," + str(chan1.voltage) + "," + time.strftime("%H:%M:%S")
    # Si el mensaje no esta vacio enviarlo al Server
    if message:
        # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
        message = message.encode('utf-8')
        message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
        client_socket.send(message_header + message)
        print("Se envio: " + str(message))
        try:
            # Now we want to loop over received messages (there might be more than one) and print them
            while True:

                # Receive our "header" containing username length, it's size is defined and constant
                username_header = client_socket.recv(HEADER_LENGTH)

                # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
                if not len(username_header):
                    print('Conexión cerrada por el servidor')
                    sys.exit()

                # Convert header to int value
                username_length = int(username_header.decode('utf-8').strip())

                # Receive and decode username
                username = client_socket.recv(username_length).decode('utf-8')

                # Now do the same for message (as we received username, we received whole message, there's no need to check if it has any length)
                message_header = client_socket.recv(HEADER_LENGTH)
                message_length = int(message_header.decode('utf-8').strip())
                message = client_socket.recv(message_length).decode('utf-8')

                # Print message
                print(f'{username} > {message}')

        except IOError as e:
            # This is normal on non blocking connections - when there are no incoming data error is going to be raised
            # Some operating systems will indicate that using AGAIN, and some using WOULDBLOCK error code
            # We are going to check for both - if one of them - that's expected, means no incoming data, continue as normal
            # If we got different error code - something happened
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print('Error: {}'.format(str(e)))
                sys.exit()

            # We just did not receive anything
            continue

        except Exception as e:
            # Any other exception - something happened, exit
            print('Error: '.format(str(e)))
            sys.exit()
