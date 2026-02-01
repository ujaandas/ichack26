# Script to reproduce Figure 1: Carbon Accumulation by Biome
# Note: The original paper used a spatial join with a Biome shapefile (Dinerstein et al. 2017) 
# to assign biomes to each site. Since that shapefile is not included in this repo,
# this script demonstrates the plotting logic using the available data.

# Check for required packages
if (!require("ggplot2")) install.packages("ggplot2")
if (!require("dplyr")) install.packages("dplyr")

library(ggplot2)
library(dplyr)

# 1. Load Data
# Adjust paths if running from a different directory
measurements <- read.csv("../data/biomass_litter_CWD.csv", stringsAsFactors = FALSE)
sites <- read.csv("../data/sites.csv", stringsAsFactors = FALSE)

# 2. Merge Data
# We need coordinates from 'sites' to (hypothetically) get biomes
data <- merge(measurements, sites, by = "site.id")

# 3. Filter Data
# Paper: "natural forest regrowth", Age <= 30
# 'refor.type' usually indicates restoration type. We'll assume 'NR' or similar is Natural Regrowth.
# Let's inspect unique refor.type if possible, but for now we filter by age.
# Variable: 'aboveground_biomass' (converted to Carbon) or 'total_plant_carbon' if available.
# The paper says they summed above+below. Here we just use what we have.

plot_data <- data %>%
  filter(stand.age > 0 & stand.age <= 30) %>%
  filter(variables.name == "aboveground_biomass") %>%
  mutate(carbon = mean_ha * 0.47) # Conversion to Carbon (approximate)

# 4. Assign Biomes (Mock Logic)
# Since we lack the Biome map, we will create a rough proxy based on Latitude
# to demonstrate the faceting used in Figure 1.
plot_data$Biome_Proxy <- case_when(
  abs(plot_data$lat_dec) > 50 ~ "Boreal",
  abs(plot_data$lat_dec) > 35 ~ "Temperate",
  abs(plot_data$lat_dec) > 23.5 ~ "Subtropical",
  TRUE ~ "Tropical"
)

# 5. Plot (Reproducing Figure 1 Style)
p <- ggplot(plot_data, aes(x = stand.age, y = carbon)) +
  geom_point(alpha = 0.5, color = "darkgreen") +
  geom_smooth(method = "lm", formula = y ~ x, color = "black") + # Linear fit as per paper
  facet_wrap(~ Biome_Proxy, scales = "free") +
  theme_bw() +
  labs(
    title = "Figure 1 Reproduction: Carbon Accumulation by Biome (Proxy)",
    subtitle = "Note: Biomes approximated by latitude as original shapefile is missing",
    x = "Stand Age (years)",
    y = "Plant Carbon (Mg C ha-1)"
  )

# Save Plot
ggsave("../outputs/figure_1_reproduction.png", plot = p, width = 10, height = 8)

print("Figure 1 reproduction saved to outputs/figure_1_reproduction.png")
