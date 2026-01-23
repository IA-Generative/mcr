# %%
"""
Explore the SUMM-RE dataset from Hugging Face.

This notebook loads examples from the 'dev' split of the 'linagora/SUMM-RE'
dataset in streaming mode and explores the data structure interactively.
"""

# %%
# Import dependencies
import io
import json
from pathlib import Path

import soundfile as sf
from datasets import Audio, load_dataset

# %%
# Load the dataset in streaming mode
print("🔍 Loading dataset linagora/SUMM-RE (split='dev', streaming=True)...")

dataset = load_dataset("linagora/SUMM-RE", split="dev", streaming=True)

# %%
# Display dataset features/columns
print("📊 Dataset features:")
print(dataset.features)

# %%
# Disable automatic audio decoding to avoid torchcodec dependency
try:
    dataset = dataset.cast_column("audio", Audio(decode=False))
    print("✅ Audio decoding disabled successfully")
except Exception as e:
    print(f"⚠️  Warning: Cannot disable audio decoding: {e}")

# %%
# Fetch first example
first_example = next(iter(dataset))
print(f"🔖 Example ID: {first_example.get('id', 'N/A')}")

# %%
# Display available keys
print("📋 Available keys in the dataset:")
for key in first_example.keys():
    print(f"  - {key}: {type(first_example[key]).__name__}")

# %%
# Display transcript
print("📝 Transcript:")
print(first_example.get("transcript", "N/A")[:500])

# %%
# Display segments structure
print("📝 Segments structure (first 2 segments):")
segments = first_example.get("segments", [])
print(json.dumps(segments[:2], indent=2, ensure_ascii=False))

# %%
# Display audio information
print("🔊 Audio information:")
audio_info = first_example.get("audio", {})
if isinstance(audio_info, dict):
    for k, v in audio_info.items():
        if k == "bytes":
            print(f"  - {k}: {len(v)} bytes")
            # Decode audio to get metadata
            try:
                audio_array, sample_rate = sf.read(io.BytesIO(v))
                print(f"  - Shape: {audio_array.shape}")
                print(f"  - Sample rate: {sample_rate} Hz")
                print(f"  - Duration: {len(audio_array) / sample_rate:.2f}s")
            except Exception as e:
                print(f"  - Decoding error: {type(e).__name__}")
        elif k == "array":
            print(f"  - {k}: <audio array>")
        else:
            print(f"  - {k}: {v}")

# %%
# Fetch multiple examples for analysis
num_examples = 3
examples = []

print(f"📥 Fetching {num_examples} examples...")
for i, example in enumerate(dataset.take(num_examples)):
    examples.append(example)
    example_id = example.get("id", f"example_{i}")
    print(f"  ✓ Example {i + 1}: {example_id}")

print(f"\n✅ Fetched {len(examples)} examples")

# %%
# Analyze segments structure across examples
print("📊 Analyzing segments structure:")
for i, example in enumerate(examples):
    segments = example.get("segments", [])
    num_segments = len(segments)

    # Check if segments have words
    has_words = segments[0].get("words") if segments else False

    print(f"\nExample {i + 1}:")
    print(f"  - Number of segments: {num_segments}")
    print(f"  - Has word-level timestamps: {bool(has_words)}")

    if segments:
        first_seg = segments[0]
        print(
            f"  - First segment: {first_seg.get('start', 'N/A'):.2f}s - {first_seg.get('end', 'N/A'):.2f}s"
        )
        print(f"  - Transcript preview: {first_seg.get('transcript', 'N/A')[:50]}...")

# %%
# Save examples locally (optional)
save_locally = True
output_dir = "./summre_samples"

if save_locally:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_path.absolute()}")

    for i, example in enumerate(examples):
        # Create filename from meeting_id, speaker_id, and audio_id
        audio_id = example.get("audio_id", f"example_{i}")

        print(f"\n💾 Saving example '{audio_id}'...")

        # Save audio
        if "audio" in example:
            audio_data = example["audio"]
            if isinstance(audio_data, dict) and audio_data.get("bytes"):
                try:
                    audio_file = output_path / f"{audio_id}.wav"
                    audio_array, sample_rate = sf.read(io.BytesIO(audio_data["bytes"]))
                    sf.write(str(audio_file), audio_array, sample_rate)
                    print(f"  ✓ Audio saved: {audio_file.name}")
                except Exception as e:
                    print(f"  ✗ Error saving audio: {e}")

        # Save transcription as JSON (excluding audio data)
        transcription_data = {k: v for k, v in example.items() if k != "audio"}

        # Convert to JSON-compatible types
        for key, value in transcription_data.items():
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                transcription_data[key] = str(value)

        json_file = output_path / f"{audio_id}.json"
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(transcription_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Transcription saved: {json_file.name}")
        except Exception as e:
            print(f"  ✗ Error saving transcription: {e}")

    print(f"\n✅ All examples saved to {output_path}")

# %%
# Download and save the entire 'dev' split
download_full_split = True  # Set to True to download the full dataset

if download_full_split:
    dev_split_dir = Path("./summre_dev_split")
    dev_split_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Starting download of full 'dev' split...")
    print(f"📁 Saving to: {dev_split_dir.absolute()}")

    # Reload dataset with disabled audio decoding
    full_dataset = load_dataset("linagora/SUMM-RE", split="dev", streaming=True)

    try:
        full_dataset = full_dataset.cast_column("audio", Audio(decode=False))
    except Exception as e:
        print(f"⚠️  Warning: Cannot disable audio decoding: {e}")

    # Track progress
    saved_count = 0
    error_count = 0

    for example in full_dataset:
        try:
            audio_id = example.get("audio_id", f"example_{saved_count}")

            # Save audio
            if "audio" in example:
                audio_data = example["audio"]
                if isinstance(audio_data, dict) and audio_data.get("bytes"):
                    try:
                        audio_file = dev_split_dir / f"{audio_id}.wav"
                        audio_array, sample_rate = sf.read(
                            io.BytesIO(audio_data["bytes"])
                        )
                        sf.write(str(audio_file), audio_array, sample_rate)
                    except Exception as e:
                        print(f"  ✗ Error saving audio for {audio_id}: {e}")
                        error_count += 1
                        continue

            # Save transcription as JSON (excluding audio data)
            transcription_data = {k: v for k, v in example.items() if k != "audio"}

            # Convert to JSON-compatible types
            for key, value in transcription_data.items():
                try:
                    json.dumps(value)
                except (TypeError, ValueError):
                    transcription_data[key] = str(value)

            json_file = dev_split_dir / f"{audio_id}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(transcription_data, f, indent=2, ensure_ascii=False)

            saved_count += 1

            # Print progress every 10 examples
            if saved_count % 10 == 0:
                print(f"  📥 Saved {saved_count} examples...")

        except Exception as e:
            print(f"  ✗ Error processing example: {e}")
            error_count += 1

    print(f"\n✅ Download complete!")
    print(f"  - Total examples saved: {saved_count}")
    print(f"  - Errors encountered: {error_count}")
    print(f"  - Location: {dev_split_dir.absolute()}")

# %%
