import librosa
import numpy as np


def line_header(title):
    print()
    print("\n" + "=" * 79 + "\n\n" + f"[ --- {title}: --- ]")
    print()


SAMPLE_RATE = 22050
FILES = [
    "Exotic.wav",
    "Enigmatic.wav",
    "Unfathomable.wav",
    "Otherworldly.wav",
    "Zenith.wav",
    "Imaginary.wav",
]


def get_spec(y):
    s = np.abs(librosa.stft(y=y, n_fft=512, hop_length=256))
    norm = np.linalg.norm(s)
    return s / norm if norm > 0 else s


loaded = {}
for f in FILES:
    try:
        y, _ = librosa.load(f, sr=SAMPLE_RATE)
        loaded[f] = {"y": y, "spec": get_spec(y)}
    except Exception as e:
        print(f"Failed to load {f}: {e}")

header = f"{'File':<16} | " + " | ".join(f"{f[:6]:<6}" for f in loaded)
line_header("Matrix Correlation")
print(header)
print("-" * len(header))

for name1, data1 in loaded.items():
    row = [f"{name1[:15]:<16}"]
    for name2, data2 in loaded.items():
        min_cols = min(data1["spec"].shape[1], data2["spec"].shape[1])
        dot = np.sum(
            data1["spec"][:, :min_cols] * data2["spec"][:, :min_cols]
        )
        row.append(f"{dot:<6.3f}")
    print(" | ".join(row))

print()
print("=" * 79)