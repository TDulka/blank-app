import streamlit as st
import pandas as pd


@st.cache_data
def load_available_sae_l0s():
    return pd.read_parquet("data/sae_split_feats.parquet")


@st.cache_data
def load_full_data():
    return pd.read_parquet("data/feature_absorption_results.parquet")


@st.cache_data
def load_sae_data(sae_l0, sae_width, layer, letter):
    df = load_full_data()
    return df[
        (df["sae_l0"] == sae_l0)
        & (df["sae_width"] == sae_width)
        & (df["layer"] == layer)
        & (df["letter"] == letter)
    ]


layer_l0_dict = {
    16000: {0: 105, 1: 102, 2: 141, 3: 59, 4: 124, 5: 68, 6: 70, 7: 69, 8: 71, 9: 73},
    65000: {0: 73, 1: 121, 2: 77, 3: 89, 4: 89, 5: 105, 6: 107, 7: 107, 8: 111, 9: 118},
}


def main():
    st.title("Feature Absorption Results Explorer")

    available_saes_df = load_available_sae_l0s()

    # Create dropdowns for filtering
    st.sidebar.header("Select an SAE")

    layers = sorted(available_saes_df["layer"].unique())
    selected_layer = st.sidebar.selectbox("Select Layer", layers, key="layer")

    sae_widths = sorted(available_saes_df["sae_width"].unique())
    selected_sae_width = st.sidebar.selectbox(
        "Select SAE Width", sae_widths, key="sae_width"
    )

    filtered_df = available_saes_df[
        (available_saes_df["layer"] == selected_layer)
        & (available_saes_df["sae_width"] == selected_sae_width)
    ]

    selected_sae_l0 = layer_l0_dict[selected_sae_width][selected_layer]

    available_letters = filtered_df[filtered_df["sae_l0"] == selected_sae_l0][
        "letter"
    ].unique()

    # Check if the previously selected letter is still available
    if (
        "selected_letter" in st.session_state
        and st.session_state.selected_letter in available_letters
    ):
        default_letter_index = list(available_letters).index(
            st.session_state.selected_letter
        )
    else:
        default_letter_index = 0

    selected_letter = st.sidebar.selectbox(
        "Select Letter", available_letters, index=default_letter_index, key="letter"
    )

    # Store the selected letter in session state
    st.session_state.selected_letter = selected_letter

    final_df = filtered_df[
        (filtered_df["sae_l0"] == selected_sae_l0)
        & (filtered_df["letter"] == selected_letter)
    ]

    st.subheader(
        f"Main First Letter Features for Layer {selected_layer}, SAE Width {selected_sae_width}, SAE L0 {selected_sae_l0}"
    )

    result_df = (
        final_df.groupby("letter")
        .agg(
            {
                "num_true_positives": "first",
                "split_feats": "first",
            }
        )
        .reset_index()
    )

    # Prepare headers for the streamlit table
    headers = ["Letter", "Num True Positives"] + [f"Feature {i}" for i in range(1, 6)]

    # Add column headers
    n_top_feats = len(result_df["split_feats"].iloc[0])
    cols = st.columns(n_top_feats + 2)
    for i, col in enumerate(cols):
        with col:
            st.write(headers[i])

    for _, row in result_df.iterrows():
        cols = st.columns(n_top_feats + 2)

        split_feats = str(row["split_feats"]).strip("[]").split()

        for i, col in enumerate(cols):
            with col:
                if i == 0:
                    st.write(row["letter"])
                elif i == 1:
                    st.write(row["num_true_positives"])
                else:
                    if i <= len(split_feats) + 1:
                        feat = split_feats[i - 2]
                        if st.button(feat, key=f"{row['letter']}_{feat}"):
                            st.session_state.clicked_feat = feat
                            st.session_state.clicked_letter = row["letter"]

    sae_link_part = f"{selected_layer}-gemmascope-res-{selected_sae_width // 1000}k"

    selected_letter_feats = result_df[result_df["letter"] == selected_letter][
        "split_feats"
    ].iloc[0]

    # Reset clicked_feat if the letter has changed
    if (
        "clicked_letter" not in st.session_state
        or st.session_state.clicked_letter != selected_letter
    ):
        st.session_state.clicked_feat = None

    # Display the default (top) feature or the clicked feature
    if st.session_state.get("clicked_feat"):
        feature_to_show = st.session_state.clicked_feat
    else:
        feature_to_show = selected_letter_feats[0]

    st.subheader(f"Split Feature {feature_to_show} for letter {selected_letter}:")

    iframe_url = f"https://neuronpedia.org/gemma-2-2b/{sae_link_part}/{feature_to_show}?embed=true"

    # Display the iframe
    st.components.v1.iframe(iframe_url, width=800, height=600, scrolling=True)

    st.subheader("Absorbing Features")

    sae_data = load_sae_data(
        selected_sae_l0, selected_sae_width, selected_layer, selected_letter
    )

    sae_data_only_absorptions = sae_data[
        (sae_data["feat_order"] == 0) & (sae_data["is_absorption"])
    ]

    feature_tokens = (
        sae_data_only_absorptions.groupby("ablation_feat")["token"]
        .apply(list)
        .reset_index()
    )

    feature_unique_tokens = {}

    for _, row in feature_tokens.iterrows():
        feature = row["ablation_feat"]
        tokens = row["token"]
        unique_tokens = list(set(tokens))  # Remove duplicates
        feature_unique_tokens[feature] = unique_tokens

    # CSS for scrollable content
    st.markdown(
        """
    <style>
    .scrollable-content {
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #ccc;
        padding: 10px;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    for feature, tokens in feature_unique_tokens.items():
        with st.expander(f"Feature: {feature}"):
            st.markdown("<div class='scrollable-content'>", unsafe_allow_html=True)
            st.write(f"Absorbing first letter on tokens: {', '.join(tokens)}")

            iframe_url = f"https://neuronpedia.org/gemma-2-2b/{sae_link_part}/{feature}?embed=true"
            st.components.v1.iframe(iframe_url, width=600, height=300, scrolling=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.write(sae_data_only_absorptions)


if __name__ == "__main__":
    main()
