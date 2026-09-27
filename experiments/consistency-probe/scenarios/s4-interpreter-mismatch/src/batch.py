def chunk(rows, size):
    return [rows[i:i + size] for i in range(0, len(rows), size)]
