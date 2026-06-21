from pathlib import Path


# =========================
# Hardcoded settings
# =========================

DECODED_OUTPUT_PATH = r"..\convertico-abstract-design-4-bit-16-colors-bmp-decoded.bmp"
BATCHES_INPUT_PATH = r"..\encoded_batches.txt"

BATCH_SIZE = 152

TYPE_BITS = 3
INDEX_BITS = 3
PAYLOAD_BITS = BATCH_SIZE - TYPE_BITS - INDEX_BITS  # 146

BATCHSIZE = PAYLOAD_BITS

TEXT_LEN_BITS = 5
HEADER_REPETITIONS = 9


# =========================
# Main output function
# =========================

def get_output_from_bits(bits_list):
    text_bits = []
    image_bits = []

    for bits in bits_list:
        bits = bits.strip()

        if len(bits) != BATCH_SIZE:
            continue

        frame_type = bits[:3]

        if frame_type == "000":
            text_bits.append(bits)

        elif frame_type == "111":
            image_bits.append(bits)

    create_text_file(text_bits)
    create_image_file(image_bits)


# =========================
# Text decoder
# =========================

def create_text_file(bits_list):
    full_text_bytes = bytearray()
    last_index = -1

    for bits in bits_list:
        index = int(bits[3:6], 2)

        # Skip duplicated frames caused by holding the same payload for several frames
        if index == last_index:
            continue

        last_index = index

        payload = bits[6:]

        used_len = int(payload[:TEXT_LEN_BITS], 2)
        data_bits = payload[TEXT_LEN_BITS:TEXT_LEN_BITS + used_len * 8]

        for i in range(0, len(data_bits), 8):
            byte_bits = data_bits[i:i + 8]

            if len(byte_bits) == 8:
                full_text_bytes.append(int(byte_bits, 2))

    text = full_text_bytes.decode("utf-8", errors="replace")

    with open("text.txt", "w", encoding="utf-8") as file:
        file.write(text)


# =========================
# Image frame decoder
# =========================

def create_image_file(image_bits):
    real_bits_list = []
    last_index = -1

    for bits in image_bits:
        index = int(bits[3:6], 2)

        # Skip duplicated frames caused by holding the same payload for several frames
        if index == last_index:
            continue

        last_index = index

        # Strip 6 bits:
        #   111 = image marker
        #   xxx = 3-bit frame index
        payload = bits[6:]

        if len(payload) == PAYLOAD_BITS:
            real_bits_list.append(payload)

    if real_bits_list:
        decode_batches_to_bmp_file(real_bits_list)


# =========================
# Bit helpers
# =========================

def bits_to_bytes(bits: str) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError("Bit string length must be divisible by 8")

    return bytes(
        int(bits[i:i + 8], 2)
        for i in range(0, len(bits), 8)
    )


def bits_to_int(bits: str) -> int:
    return int(bits, 2)


def majority(bits: str) -> str:
    ones = bits.count("1")
    zeros = bits.count("0")
    return "1" if ones >= zeros else "0"


# =========================
# Optional: load batches from a text file
# =========================

def load_batches_from_file() -> list[str]:
    text = Path(BATCHES_INPUT_PATH).read_text(encoding="utf-8")

    batches = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for batch in batches:
        if len(batch) != PAYLOAD_BITS:
            raise ValueError(
                f"Invalid batch size: expected {PAYLOAD_BITS}, got {len(batch)}"
            )

        if any(bit not in "01" for bit in batch):
            raise ValueError("Batch file contains characters other than 0 and 1")

    return batches


# =========================
# BMP raw-file decoder
# =========================

def decode_header(bit_string: str) -> tuple[int, int]:
    """
    Header format:

        magic number - 32 bits
        file size    - 64 bits

    Repeated HEADER_REPETITIONS times.
    """

    raw_header_size = 96
    full_header_size = raw_header_size * HEADER_REPETITIONS

    if len(bit_string) < full_header_size:
        raise ValueError("Not enough bits to read the header")

    header_bits = bit_string[:full_header_size]

    recovered_bits = []

    for i in range(raw_header_size):
        copies = ""

        for r in range(HEADER_REPETITIONS):
            copies += header_bits[r * raw_header_size + i]

        recovered_bits.append(majority(copies))

    recovered = "".join(recovered_bits)

    magic = bits_to_int(recovered[0:32])
    file_size = bits_to_int(recovered[32:96])

    if magic != 0xBEEFCAFE:
        raise ValueError("Header is too damaged or not from the matching encoder")

    return file_size, full_header_size


def decode_batches_to_bmp_file(batches: list[str]) -> None:
    bit_string = "".join(batches)

    file_size, data_start = decode_header(bit_string)

    data_bits_needed = file_size * 8

    bmp_bits = bit_string[data_start:data_start + data_bits_needed]

    if len(bmp_bits) < data_bits_needed:
        raise ValueError("Not enough bits to reconstruct the BMP file")

    bmp_data = bits_to_bytes(bmp_bits)

    Path(DECODED_OUTPUT_PATH).write_bytes(bmp_data)


# =========================
# Main
# =========================

if __name__ == "__main__":
    # This direct mode is only for testing raw image batches from encoded_batches.txt.
    # For your video scanner, call:
    #
    #     get_output_from_bits(bits_list)
    #
    # where bits_list contains full 152-bit frames.
    batches = load_batches_from_file()
    decode_batches_to_bmp_file(batches)

    print(f"Loaded {len(batches)} raw image batches")
    print(f"Decoded BMP saved to: {DECODED_OUTPUT_PATH}")