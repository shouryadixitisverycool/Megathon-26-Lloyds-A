"""Run with streamlit run src/greenr/app/main.py or the installed package path."""

import streamlit as st

from greenr.app.client import APIClient, APIError
from greenr.app.views import customer_view, portfolio_view
from greenr.app.workspaces import governance_view, planning_view, rm_view

st.set_page_config(page_title="Greenr | Synthetic demo", page_icon=":material/forest:", layout="wide")


@st.cache_data(ttl=15, max_entries=128, show_spinner=False)
def load_json(base_url, path, params=()):
    return APIClient(base_url).get(path, dict(params))


st.title("Greenr", icon=":material/forest:")
st.caption("A FIELD GUIDE TO RESPONSIBLE OPPORTUNITIES")
st.badge("Synthetic demo", color="orange", icon=":material/science:")
st.caption("Product relevance only. This demonstration does not establish real-world predictive performance or credit eligibility.")

with st.sidebar:
    st.header("Greenr", icon=":material/forest:")
    view = st.radio("Workspace", ["Customer", "Portfolio", "Relationship Manager", "Planning", "Governance"], key="workspace")
    if st.button("Refresh data", icon=":material/refresh:", key="refresh", width="stretch"):
        load_json.clear()
    st.caption("API responses cache for up to 15 seconds. Refresh data requests fresh responses.")

try:
    client = APIClient()
    health = client.get("/health")  # Never use cached data to conceal an unreachable service.
    if health.get("status") != "ok" or health.get("synthetic_demo") is not True:
        raise APIError("This app requires a healthy synthetic-demo API.")
    st.sidebar.caption("Contract: " + health["contract_version"])
    if health.get("provider_mode"):
        st.sidebar.caption("Data source: " + health["provider_mode"])
    if health.get("source_version"):
        st.sidebar.caption("Source version: " + health["source_version"])

    def load(path, params=None):
        return load_json(client.base_url, path, tuple(sorted((params or {}).items())))

    def save(path, payload):
        result = client.post(path, payload)
        load_json.clear()
        return result

    customers = load("/customers")
    if not isinstance(customers, list):
        raise APIError("The API customer list has an invalid response shape.")
    if not customers:
        st.info("No synthetic customers are available from the API.")
    elif view == "Customer":
        customer_view(customers, load, save, health.get("provider_mode"))
    elif view == "Portfolio":
        portfolio_view(customers, load)
    elif view == "Relationship Manager":
        rm_view(customers, load, save)
    elif view == "Planning":
        planning_view(customers, load, save)
    elif view == "Governance":
        governance_view(load)
except APIError as error:
    st.error(str(error), icon=":material/cloud_off:")
    st.caption("No customer decisions or portfolio results are displayed while this request is unavailable.")
except (KeyError, TypeError, ValueError) as error:
    st.error("The API response does not match this UI contract. Refresh data or check the API version.")
    st.caption("Incomplete results cannot be interpreted as a recommendation.")
