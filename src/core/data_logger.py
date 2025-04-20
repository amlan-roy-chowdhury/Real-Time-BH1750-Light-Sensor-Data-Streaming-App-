# src/core/data_logger.py
import os
import csv
import datetime

def write_summary_csv(filepath, session_data):
    try:
        with open(filepath, mode='w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["Relative Timestamp (ms)", "GMT Timestamp", "Lux"])
            for rel_ts, gmt_ts, lux in session_data:
                writer.writerow([rel_ts, gmt_ts, lux])

            writer.writerow([])
            writer.writerow(["Summary"])
            writer.writerow(["Min", "Max", "Avg"])

            lux_values = [entry[2] for entry in session_data]
            if lux_values:  # handle empty list
                writer.writerow([
                    f"{min(lux_values):.2f}",
                    f"{max(lux_values):.2f}",
                    f"{sum(lux_values)/len(lux_values):.2f}"
                ])
            else:
                writer.writerow(["--", "--", "--"])
        return True
    except Exception as e:
        print(f"[Write CSV Failed]: {e}")
        return False


def write_temp_log(temp_path, session_data):
    try:
        with open(temp_path, mode='a', newline='') as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow([f"--- SESSION START: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"])
            writer.writerow(["Relative Timestamp (ms)", "GMT Timestamp", "Lux"])
            for rel_ts, gmt_ts, lux in session_data:
                writer.writerow([rel_ts, gmt_ts, lux])
            writer.writerow([])
            writer.writerow(["Summary"])
            lux_values = [entry[2] for entry in session_data]
            writer.writerow(["Min", "Max", "Avg"])
            writer.writerow([
                f"{min(lux_values):.2f}",
                f"{max(lux_values):.2f}",
                f"{sum(lux_values)/len(lux_values):.2f}"
            ])
            writer.writerow([f"--- SESSION END ---", "", ""])
    except Exception as e:
        print(f"[Temp Log Export Failed]: {e}")
