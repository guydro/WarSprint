def get_output_from_bits(bits_list):
    text_bits = []
    image_bits = []

    for bits in bits_list:
        if bits[:3] == "000":
            text_bits.append(bits)
        elif "1" in bits:
            image_bits.append(bits)

    create_text_file(text_bits)
    create_image_file(image_bits)

    #TODO: deal with looparound

def create_text_file(bits_list):
    full_text = ""
    last_index = -1
    for bits in bits_list:
        index, text = text_from_batch(bits[3:])
        if index != last_index:
            last_index = index
            full_text += text

    with open("text.txt", "w", encoding="utf-8") as file:
        file.write(full_text)

def create_image_file(image_bits):
    real_bits_list = []
    last_index = -1

    for bits in image_bits:
        index = int(bits[3:6], 2)

        if index != last_index:
            real_bits_list.append(bits[6:])
            last_index = index

    decode_batches_to_bmp_file(real_bits_list)



def text_from_batch(bits):
    index = int(bits[:3], 2)
    text = ""
    cnt_char = ""
    for char in bits[3:]:
        cnt_char += char
        if len(cnt_char) >= 8:
            text += chr(int(cnt_char, 2))
            cnt_char = ""

    return index, text

# =========================
# Hardcoded settings
# =========================

IMAGE_PATH = r"C:\Users\TLP\OneDrive\Desktop\sprint4\convertico-abstract-design-4-bit-16-colors-bmp.bmp"
DECODED_OUTPUT_PATH = r"C:\Users\TLP\OneDrive\Desktop\sprint4\convertico-abstract-design-4-bit-16-colors-bmp-decoded.bmp"
BATCHES_INPUT_PATH = r"C:\Users\TLP\Desktop\encoded_batches.txt"

batch_size = 152
BATCHSIZE = batch_size - 3
from pathlib import Path

# =========================
# Hardcoded settings
# =========================

HEADER_REPETITIONS = 9


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
# Load batches
# =========================

def load_batches_from_file() -> list[str]:
    text = Path(BATCHES_INPUT_PATH).read_text(encoding="utf-8")

    batches = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for batch in batches:
        if len(batch) != BATCHSIZE:
            raise ValueError(f"Invalid batch size: expected {BATCHSIZE}, got {len(batch)}")

        if any(bit not in "01" for bit in batch):
            raise ValueError("Batch file contains characters other than 0 and 1")

    return batches


# =========================
# Header decoder
# =========================

def decode_header(bit_string: str) -> tuple[int, int]:
    """
    Header format from the raw-BMP encoder:

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


# =========================
# Decoder
# =========================

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
    batches = load_batches_from_file()
    decode_batches_to_bmp_file(batches)

    print(f"Loaded {len(batches)} batches")
    print(f"Decoded BMP saved to: {DECODED_OUTPUT_PATH}")