import os
import json

def get_keys_with_compact_values(path="."):
    result = {}

    for file in os.listdir(path):
        if file.endswith(".json"):
            file_key_info = {}
            try:
                with open(os.path.join(path, file), "r", encoding="utf-8") as f:
                    data = json.load(f)

                def extract_keys(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if k not in file_key_info:
                                file_key_info[k] = {"types": set(), "values": set()}
                            file_key_info[k]["types"].add(type(v).__name__)

                            # Store only simple examples
                            if len(file_key_info[k]["values"]) < 3:
                                if isinstance(v, (str, int, float, bool, type(None))):
                                    if isinstance(v, str) and len(v) > 50:  # truncate long strings
                                        file_key_info[k]["values"].add(v[:50] + "...")
                                    else:
                                        file_key_info[k]["values"].add(v)
                                elif isinstance(v, (list, dict)):
                                    # store type and length instead of full content
                                    file_key_info[k]["values"].add(f"<{type(v).__name__} len={len(v)}>")

                            extract_keys(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            extract_keys(item)

                extract_keys(data)
                result[file] = file_key_info

            except Exception as e:
                print(f"Skipping {file} due to error: {e}")

    return result

if __name__ == "__main__":
    per_file_keys = get_keys_with_compact_values(".")
    output_file = "json_keys_report.txt"

    with open(output_file, "w", encoding="utf-8") as out:
        for file, keys in per_file_keys.items():
            out.write(f"\nFile: {file}\n")
            for k in sorted(keys):
                types_str = ', '.join(sorted(keys[k]["types"]))
                values_list = list(keys[k]["values"])
                out.write(f"  {k}: types={types_str}, sample_values={values_list}\n")

    print(f"Output saved to {output_file}")
