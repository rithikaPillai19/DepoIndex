import json
import pandas as pd

df = pd.read_csv("Persis_Yu_Topic_Index.csv")

print("=== Production Index Summary ===")
print(f"Total Substantive Topics: {len(df)}")
print(f"First Row Start : {df.iloc[0]['Start']} ({df.iloc[0]['Topic']})")
print(f"Final Row End   : {df.iloc[-1]['End']} ({df.iloc[-1]['Topic']})")

print("\n=== First 3 Rows ===")
for i in range(min(3, len(df))):
    print(f"[{i}] {df.iloc[i]['Start']} -> {df.iloc[i]['End']} | {df.iloc[i]['Topic']}")

print("\n=== Last 3 Rows ===")
for i in range(max(0, len(df)-3), len(df)):
    print(f"[{i}] {df.iloc[i]['Start']} -> {df.iloc[i]['End']} | {df.iloc[i]['Topic']}")

print("\n=== Quarantine Audit Summary ===")
with open("output/quarantine_audit.json", "r", encoding="utf-8") as f:
    quarantine = json.load(f)

print(f"Total Quarantined Entries: {len(quarantine)}")
if quarantine:
    first_q = quarantine[0]
    print(f"Sample Intercepted Topic: {first_q.get('topic')}")
    print(f"Reason(s): {first_q.get('failures', first_q.get('reasons'))}")