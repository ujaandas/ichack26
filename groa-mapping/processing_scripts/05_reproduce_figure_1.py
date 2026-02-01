import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Define paths
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
DATA_DIR = os.path.join(repo_root, "data")
OUTPUT_DIR = os.path.join(repo_root, "outputs")

def reproduce_figure_1_improved():
    print("Loading data...")
    try:
        measurements = pd.read_csv(os.path.join(DATA_DIR, "biomass_litter_CWD.csv"), encoding='latin1')
        sites = pd.read_csv(os.path.join(DATA_DIR, "sites.csv"), encoding='latin1')
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Merge Data
    data = pd.merge(measurements, sites, on="site.id")

    # Filter Data
    # Paper: "natural forest regrowth", Age <= 30
    # Variable: 'aboveground_biomass'
    plot_data = data[
        (data['stand.age'] > 0) & 
        (data['stand.age'] <= 30) & 
        (data['variables.name'] == 'aboveground_biomass')
    ].copy()

    # Convert to Carbon (approximate)
    plot_data['carbon'] = plot_data['mean_ha'] * 0.47

    # Assign Biomes (Improved Logic based on Climate)
    # Note: This is an approximation. The original paper used a spatial join with Dinerstein et al. 2017.
    
    def assign_biome(row):
        lat = abs(row['lat_dec'])
        amt = row['AMT'] # Temp
        amp = row['AMP'] # Precip
        
        # Handle missing climate data
        if pd.isna(amt) or pd.isna(amp):
            # Fallback to simple latitude
            if lat > 50: return "Boreal"
            if lat > 23.5: return "Temperate"
            return "Tropical Moist" # Default for tropics if unknown

        # Boreal
        if lat > 50 or amt < 3:
            return "Boreal"
        
        # Temperate
        if lat > 23.5:
            # Attempt to split Conifer vs Broadleaf? 
            # Very hard without species/region. 
            # Let's keep them grouped or try a rough precip split?
            # Paper: Temperate Conifer vs Temperate Broadleaf
            # Broadleaf often wetter/warmer in some contexts, but Conifer rainforests exist.
            # Let's group them as "Temperate (Broadleaf & Conifer)" to be honest about the proxy.
            return "Temperate" 
            
        # Tropical / Subtropical
        if lat <= 23.5:
            if amp < 1000:
                return "Tropical Dry"
            elif amp < 1500:
                return "Tropical Savanna"
            else:
                return "Tropical Moist"
        
        return "Other"

    plot_data['Biome_Proxy'] = plot_data.apply(assign_biome, axis=1)

    print(f"Plotting {len(plot_data)} points...")
    print("Biome counts:")
    print(plot_data['Biome_Proxy'].value_counts())

    # Plotting
    sns.set_theme(style="whitegrid")
    
    # Create a FacetGrid
    g = sns.lmplot(
        data=plot_data, 
        x="stand.age", 
        y="carbon", 
        col="Biome_Proxy", 
        col_wrap=3, # 3 columns to fit 5-6 plots nicely
        height=4, 
        aspect=1.0,
        scatter_kws={'alpha': 0.4, 's': 15, 'color': 'darkgreen'},
        line_kws={'color': 'black', 'linewidth': 1.5}
    )

    # Titles and Labels
    g.fig.suptitle("Figure 1 Reproduction: Carbon Accumulation by Biome (Climate Proxy)", y=1.02, fontsize=16)
    g.set_axis_labels("Stand Age (years)", "Plant Carbon (Mg C ha-1)")
    g.set_titles("{col_name}")
    
    # Save
    output_path = os.path.join(OUTPUT_DIR, "figure_1_reproduction_improved.png")
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    print(f"Figure saved to: {output_path}")

if __name__ == "__main__":
    reproduce_figure_1_improved()
