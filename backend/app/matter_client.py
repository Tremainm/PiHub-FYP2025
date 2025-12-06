import re
import subprocess

def read_temperature():
    try:
        result = subprocess.run(
            [
                "/snap/bin/chip-tool",
                "temperaturemeasurement",
                "read",
                "measured-value",
                "1",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout + result.stderr

        # Remove ANSI color codes
        output = re.sub(r'\x1B\[[0-9;]*[mK]', '', output)

        # Look for MeasuredValue: <number>
        match = re.search(r"MeasuredValue:\s*(-?\d+)", output)
        if not match:
            raise ValueError(f"Could not parse temperature from output:\n{output}")

        raw_value = int(match.group(1))
        temp_c = raw_value / 100.0
        return temp_c

    except Exception as e:
        raise Exception(f"Matter read failed: {e}")
