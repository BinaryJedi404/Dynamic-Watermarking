import streamlit as st
import re
import os
import random
from functools import reduce
from tkinter import filedialog
import tkinter as tk

UPLOAD_FOLDER = '.'
ALLOWED_EXTENSIONS = {'txt', 'py'}

st.set_page_config(page_title="Watermarking Tool", layout="wide")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def encode_signature(signature, primes):
    primes = list(map(int, primes.split(",")))
    product = reduce((lambda x, y: x * y), primes)
    if product < signature:
        st.warning(
            "Product of prime numbers is less than the signature. Please refill the signature value.")
        return None, None
    B = []
    for p in primes:
        B.append(signature % p)
    return B, product


def generate_stego_programs(B):
    stego_programs = []
    for i, b in enumerate(B):
        k = random.randint(5, 20)
        r = random.randint(1, 10)
        stego_program = f"W{i} = {b - r * k}\n"
        stego_program += f"for _ in range({k}):\n"
        stego_program += f"  W{i} += {r}\n"
        stego_programs.append(stego_program)
    return stego_programs


def find_insertion_points(lines):
    insertion_points = []
    for i, line in enumerate(lines):
        if re.match(r"def\s+\w+\s*\(", line):
            insertion_points.append(i)
    return insertion_points


def get_indentation_level(line):
    return len(line) - len(line.lstrip())


def find_insertion_point(segment):
    insertion_points = []
    for i, line in enumerate(segment):
        indentation_level = get_indentation_level(line)
        if line.endswith(':'):
            continue
        if indentation_level <= 1:
            insertion_points.append(i)
    if insertion_points:
        return random.choice(insertion_points)
    else:
        # If no suitable insertion point found, append at the end
        return len(segment)


def embed_stego_programs(stego_programs, normal_program):
    lines = normal_program.split("\n")
    insertion_points = find_insertion_points(lines)

    segments = []
    start = 0
    for end in insertion_points:
        segment = lines[start:end]
        segments.append(segment)
        start = end
    segments.append(lines[start:])

    embedded_program = ""
    for i, segment in enumerate(segments):
        if i < len(stego_programs):
            insertion_point = find_insertion_point(segment)
            indentation = get_indentation_level(segment[insertion_point])
            stego_program = stego_programs[i].split('\n')
            stego_program = [
                f"{' ' * (indentation-1)}{line}" for line in stego_program]
            segment = segment[:insertion_point] + \
                stego_program + segment[insertion_point:]
        embedded_program += "\n".join(segment) + "\n"

    return embedded_program


def extract_stego_programs(code):
    stegoprograms = []
    pattern = r'W\d+\s*=\s*-?\d+\s*for\s*_\s*in\s*range\s*\(\s*\d+\s*\)\s*:\s*W\d+\s*\+=\s*-?\d+'
    matches = re.findall(pattern, code)
    for match in matches:
        stegoprograms.append(match.strip())
    return stegoprograms


def extract_signature(stego_programs, primes, signarurev):
    W = []
    for stego in stego_programs:
        lines = stego.split("\n")
        init_val = int(lines[0].split(" = ")[1])
        updates = int(lines[1].split("(")[1].split(")")[0])
        final_val = init_val + updates * int(lines[2].split(" += ")[1])
        W.append(final_val)
    primes = list(map(int, primes.split(',')))
    N = reduce((lambda x, y: x * y), primes)
    signature = 0
    for i, b in enumerate(W):
        R = N // primes[i]
        x = pow(R, -1, primes[i])
        signature += b * R * x
    return "Verified" if (signature % N)==(signarurev) else "Not the owner"


def save_file(content, filename):
    with open(filename, 'w') as f:
        f.write(content)


def main():
    st.title("Dynamic Software Watermarking Tool")

    option = st.sidebar.selectbox(
        'Choose an action:', ['Generate Watermarked Program', 'Extract Signature'])

    if option == 'Generate Watermarked Program':
        st.header('Generate Watermarked Program')
        file = st.file_uploader(
            "Upload Normal Program File", type=['txt', 'py'])

        if file is not None:
            signature = st.text_input("Enter Signature:")
            primes = st.text_input("Enter Prime Numbers (comma-separated):")

            if st.button("Generate Watermarked Program"):
                if signature and primes:
                    normal_program = file.getvalue().decode("utf-8")
                    B, product = encode_signature(int(signature), primes)
                    if B:
                        st.write(f"Product of prime numbers: {product}")
                        stego_programs = generate_stego_programs(B)
                        watermarked_program = embed_stego_programs(
                            stego_programs, normal_program)

                        st.write(
                            "Select where to save the watermarked program:")
                        root = tk.Tk()
                        root.withdraw()
                        file_path = filedialog.asksaveasfilename(
                            defaultextension=".py")
                        if file_path:
                            save_file(watermarked_program, file_path)
                            st.code(watermarked_program, language='python')
                            watermarked_filename = f"watermarked_{file.name}"
                            with open(os.path.join(UPLOAD_FOLDER, watermarked_filename), 'w') as f:
                                f.write(watermarked_program)
                            st.success(
                                f"Watermarked program saved successfully as '{file_path}'")
                        else:
                            st.warning(
                                "No file selected. Watermarked program not saved.")
                else:
                    st.error("Please enter both signature and prime numbers.")

    elif option == 'Extract Signature':
        st.header('Extract Signature from Watermarked Program')
        file = st.file_uploader(
            "Upload Watermarked Program File", type=['txt', 'py'])

        if file is not None:
            primes = st.text_input("Enter Prime Numbers (comma-separated):")
            signaturev = st.text_input("Enter Signature:")
            if st.button("Extract Signature"):
                if primes:
                    watermarked_program = file.getvalue().decode("utf-8")
                    stego_programs = extract_stego_programs(
                        watermarked_program)
                    signature = extract_signature(stego_programs, primes,int(signaturev))
                    st.success(f"Extracted signature: {signature}")
                else:
                    st.error("Please enter prime numbers.")


if __name__ == "__main__":
    main()
