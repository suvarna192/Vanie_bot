import websockets
import asyncio
import threading
import logging
import http.server
import socketserver
import os
import signal
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import smtplib
from originalAnswergeneration import final_result,initialize_components
import textwrap
  # Assuming final_result is in answer_generation.py
# from answer_generation1 import final_result  # Assuming final_result is in answer_generation.py

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server data
HOST = '192.168.230.64'
PORT = 7898
HTTP_PORT = 8006  # Port for serving HTML file
logger.info("Server listening on Port %d", PORT)

# Dictionary to store session IDs for each WebSocket connection
sessions = {}
context = {}
dialogue_state = {}

# Flag to indicate whether the HTTP server should keep serving
http_server_running = True

# Function to handle logging for each session
def setup_logging(session_id):
    log_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    log_file = os.path.join(log_directory, f"{session_id}.log")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    session_logger = logging.getLogger(session_id)
    session_logger.addHandler(handler)
    session_logger.setLevel(logging.INFO)
    return session_logger

# Function to handle logging for errors
def setup_error_logging():
    error_log_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
    if not os.path.exists(error_log_directory):
        os.makedirs(error_log_directory)
    error_log_file = os.path.join(error_log_directory, "error.log")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(error_log_file)
    handler.setFormatter(formatter)
    error_logger = logging.getLogger("error_logger")
    error_logger.addHandler(handler)
    error_logger.setLevel(logging.ERROR)
    return error_logger

# Initialize error logger
error_logger = setup_error_logging()
async def echo(websocket, path):
    session_id = str(id(websocket))
    sessions[session_id] = websocket
    context[session_id] = []
    dialogue_state[session_id] = ""

    logger.info("A client connected with session ID: %s", session_id)

    try:
        async for message in websocket:
            context[session_id].append(message)

            try:
                # ✅ Call final_result asynchronously
                response = await final_result(message)  
                logger.info(f"Response from final_result: {response}")

            except Exception as e:
                response = "An error occurred while processing your request."
                logger.error(f"Error querying final_result: {str(e)}")

            # Send response back to WebSocket client
            await websocket.send(response)

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client with session ID {session_id} disconnected")
    finally:
        del sessions[session_id]


# Function to serve HTML file
def serve_html():
    Handler = http.server.SimpleHTTPRequestHandler

    # Initialize SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    certfile_path = "/home/sumasoft/Sumabot_LLM/sumasoft.com/sumasoft.com.pem"
    keyfile_path = "/home/sumasoft/Sumabot_LLM/sumasoft.com/sumasoft.key.pem"
    ssl_context.load_cert_chain(certfile=certfile_path, keyfile=keyfile_path)

    # Create HTTPS server
    httpd = socketserver.TCPServer(("", HTTP_PORT), Handler)
    httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)

    logger.info("Serving HTML file at https://%s:%d/client1.html", HOST, HTTP_PORT)

    # Start serving indefinitely
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

initialize_components()

# Start the WebSocket server
def start_websocket_server():
    # Initialize SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    certfile_path = "/home/sumasoft/Sumabot_LLM/sumasoft.com/sumasoft.com.pem"
    keyfile_path = "/home/sumasoft/Sumabot_LLM/sumasoft.com/sumasoft.key.pem"
    ssl_context.load_cert_chain(certfile=certfile_path, keyfile=keyfile_path)

    # Start WebSocket server with SSL support
    ws_server = websockets.serve(echo, HOST, PORT, ssl=ssl_context)
    asyncio.get_event_loop().run_until_complete(ws_server)

# Function to handle SIGINT (ctrl+c)
def signal_handler(sig, frame):
    global http_server_running
    if http_server_running:
        # Shut down the HTTP server and WebSocket server gracefully
        logger.info("Shutting down the server...")
        http_server_running = False
        asyncio.get_event_loop().stop()

# Register signal handler for SIGINT
signal.signal(signal.SIGINT, signal_handler)

# Start the HTTP server in a separate thread
html_thread = threading.Thread(target=serve_html)
html_thread.start()

# Start the WebSocket server
start_websocket_server()

# Run the event loop indefinitely
asyncio.get_event_loop().run_forever()
