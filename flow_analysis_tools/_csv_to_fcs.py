import pandas as pd
import flowkit as fk
import flowio
import numpy as np

def csv_to_fcs(csv_file_path, fcs_file_path, voltages):
    # 1. Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file_path)
    
    # Ensure all data is numeric (FCS files store numeric data)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()

    # 3. Define metadata (channel names are mandatory)
    exclude_cols = ['Absolute Event', 'Event', 'Relative Event']
    channel_labels = [c for c in df.columns if c not in exclude_cols]
    df = df[channel_labels]

    # 2. Convert the DataFrame to a NumPy array for FlowIO compatibility
    event_data = df.to_numpy()

    
    # FlowIO requires specific metadata structure, including PnN for channel names
    # and PnR for ranges. FlowKit handles some of this internally.
    
    # Use FlowKit to create a sample object, which handles the complex metadata generation
    sample = fk.Sample(event_data, channel_labels=channel_labels, sample_id=csv_file_path)

    for v_label, v in voltages.items():
        sample.metadata[v_label] = v

    # 4. Use FlowIO to write the data to an FCS file
    # The write_fcs method handles creating the FCS header and data segments correctly
    sample.export(fcs_file_path, source="raw", include_metadata=True)

    print(f"Successfully converted {csv_file_path} to {fcs_file_path}")
