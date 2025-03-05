import socket
import logging
import time
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("leecher_debug.log"),
                        logging.StreamHandler()
                    ])

# Configuration
TRACKER_ADDR = (socket.gethostbyname(socket.gethostname()), 6020)
FORMAT = 'utf-8'
CHUNK_SIZE = 512
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

class FileLeecher:
    def __init__(self, filename):
        self.filename = filename
        self.leecher_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def get_seeders(self):
        try:
            logging.debug("Sending seeders request to tracker")
            self.leecher_udp.sendto(f"REQUEST_SEEDERS {self.filename}".encode(FORMAT), TRACKER_ADDR)
            
            # Longer timeout for UDP
            self.leecher_udp.settimeout(30)
            
            data, _ = self.leecher_udp.recvfrom(1024)
            seeders_response = data.decode(FORMAT).split()
            
            logging.debug(f"Seeders response: {seeders_response}")
            
            if seeders_response[0] == "NO_SEEDERS":
                logging.error("No seeders available.")
                return []
            
            return seeders_response[1:]
        
        except socket.timeout:
            logging.error("Timeout while requesting seeders")
            return []
        except Exception as e:
            logging.error(f"Error getting seeders: {e}")
            logging.error(traceback.format_exc())
            return []

    def download_from_seeder(self, seeder_addr):
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            ip, port = seeder_addr.split(":")
            seeder_socket_addr = (ip, int(port))
            
            logging.debug(f"Attempting to connect to seeder: {seeder_socket_addr}")
            
            # Longer connection timeout
            tcp_client.settimeout(60)
            
            # Connect with detailed logging
            for attempt in range(MAX_RETRIES):
                try:
                    tcp_client.connect(seeder_socket_addr)
                    logging.info(f"Connected to seeder {seeder_socket_addr}")
                    break
                except Exception as connect_err:
                    logging.warning(f"Connection attempt {attempt + 1} failed: {connect_err}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        raise
            
            # Get total chunks
            logging.debug("Requesting chunk count")
            tcp_client.sendall(f"GET_CHUNK_COUNT {self.filename}".encode(FORMAT))
            total_chunks = int(tcp_client.recv(1024).decode(FORMAT))
            logging.info(f"Total chunks: {total_chunks}")
            
            # Download chunks
            chunks = []
            for chunk_id in range(total_chunks):
                logging.debug(f"Downloading chunk {chunk_id}")
                tcp_client.sendall(f"GET_CHUNK {self.filename} {chunk_id}".encode(FORMAT))
                
                # Retry chunk download with detailed logging
                for retry in range(MAX_RETRIES):
                    try:
                        chunk = tcp_client.recv(CHUNK_SIZE)
                        if not chunk:
                            raise ValueError("Empty chunk received")
                        chunks.append(chunk)
                        logging.debug(f"Successfully downloaded chunk {chunk_id}")
                        break
                    except Exception as chunk_err:
                        logging.warning(f"Chunk {chunk_id} download retry {retry + 1}: {chunk_err}")
                        if retry == MAX_RETRIES - 1:
                            logging.error(f"Failed to download chunk {chunk_id}: {chunk_err}")
                            logging.error(traceback.format_exc())
                            raise
                        time.sleep(RETRY_DELAY)
            
            return chunks
        
        except Exception as e:
            logging.error(f"Download error from {seeder_addr}: {e}")
            logging.error(traceback.format_exc())
            return None
        finally:
            try:
                tcp_client.close()
            except:
                pass

    def download_file(self):
        # Get list of seeders
        seeders = self.get_seeders()
        
        if not seeders:
            logging.error("No seeders found.")
            return False
        
        # Try downloading from each seeder
        for seeder in seeders:
            logging.info(f"Attempting to download from seeder: {seeder}")
            chunks = self.download_from_seeder(seeder)
            
            if chunks:
                # Save downloaded file
                try:
                    with open(f"downloaded_{self.filename}", "wb") as f:
                        for chunk in chunks:
                            f.write(chunk)
                    logging.info(f"File {self.filename} downloaded successfully.")
                    return True
                except Exception as e:
                    logging.error(f"Error saving file: {e}")
                    logging.error(traceback.format_exc())
        
        logging.error("Failed to download file from all seeders.")
        return False

def main():
    filename = "sample.txt"
    leecher = FileLeecher(filename)
    leecher.download_file()

if __name__ == "__main__":
    main()