"""Source-linked SiteMinder findings for the Market Intelligence overview."""

import streamlit as st

from ui.components import dashboard_card

# Consolidated reported revenue (A$ millions) and monthly transaction ARPU (A$).
# FY24/FY25: FY25 Annual Report PDF p. 13. FY26: FY26 Annual Report PDF p. 12.
REVENUE_HISTORY = (
    ("FY24", 190.673, 122.378, 68.295, 132),
    ("FY25", 224.327, 139.073, 85.254, 155),
    ("FY26", 266.061, 155.206, 110.855, 179),
)

FY25_REPORT = "https://www.siteminder.com/wp-content/uploads/2025/08/250827_FY25-Annual-Report.pdf"
FY26_REPORT = "https://www.siteminder.com/wp-content/uploads/2026/08/Annual-Report-SiteMinder-FY26.pdf"
FY26_PRESENTATION = "https://www.siteminder.com/wp-content/uploads/2026/08/Presentation-SiteMinder-FY26.pdf"
AGM_PRESENTATION = "https://www.siteminder.com/wp-content/uploads/2026/10/Annual-General-Meeting.pdf"


def siteminder_research() -> None:
    with dashboard_card("siteminder-research"):
        st.subheader("SiteMinder | How the revenue mix changed", anchor=False)
        st.caption("ASX: SDR · Public company disclosures · FY24–FY26, years ended 30 June · AUD")
        st.markdown(
            "**Transactions contributed 61.3% of FY26 reported revenue growth.** "
            "That makes product attachment and repeat usage worth investigating when evaluating "
            "growth in the existing customer base."
        )
        st.dataframe(
            [
                {
                    "Fiscal year": year,
                    "Total (A$m)": f"{total:.3f}",
                    "Subscriptions (A$m)": f"{subscriptions:.3f}",
                    "Transactions (A$m)": f"{transactions:.3f}",
                    "Transaction share": f"{transactions / total:.1%}",
                    "Monthly transaction ARPU (A$)": arpu,
                }
                for year, total, subscriptions, transactions, arpu in REVENUE_HISTORY
            ],
            width="stretch",
            hide_index=True,
            alt="SiteMinder consolidated revenue and monthly transaction ARPU, FY24 to FY26",
        )
        st.markdown(
            "**Customer monetization.** In FY26, reported transaction revenue grew **30.0%**, "
            "versus **11.6%** for subscriptions. Monthly transaction ARPU rose from AUD 132 in FY24 "
            "to AUD 179 in FY26. The aggregate figures combine product usage, customer mix, and "
            "commercial terms. They cannot isolate cross-sell uplift."
        )
        st.markdown(
            "**Product developments.** At FY26, management reported almost 10,000 hotels for "
            "Channels Plus and more than 50,000 rooms supported by Dynamic Revenue Plus. "
            "These measure product reach in different units. The October 2026 AGM described "
            "Dynamic Revenue Plus 2.0 as planned for January 2027."
        )
        with st.expander("Metric definitions, limitations and primary sources"):
            st.markdown(
                "- **Revenue.** Consolidated reported AUD. Note 5 recognizes subscription revenue "
                "over time and transaction revenue at a point in time. Transactions span multiple "
                "products. The FY25 report flags a FY24 Demand Plus recognition-timing change. "
                f"[FY25 Annual Report, 27 Aug 2025, PDF pp. 13, 70–71]({FY25_REPORT}) · "
                f"[FY26 Annual Report, 25 Aug 2026, PDF pp. 12–13, 70]({FY26_REPORT})\n"
                "- **Calculated shares.** Transaction share divides transaction revenue by total "
                "revenue. The 61.3% divides the FY26 increase in transaction revenue (AUD 25.601 million) "
                "by the increase in total revenue (AUD 41.734 million).\n"
                "- **Monthly transaction ARPU.** Transaction and other revenue per property per "
                "month across the total property base. Transaction product uptakes can count "
                "multiple products at one property. Neither measure establishes eligible "
                "non-adopters, product margins, or product retention. "
                f"[FY26 Investor Presentation, 25 Aug 2026, PDF pp. 35–37, 48–49]({FY26_PRESENTATION})\n"
                "- **Product milestones.** Company-reported reach and then-stated plans. "
                f"[FY26 Investor Presentation, PDF pp. 25–26]({FY26_PRESENTATION}) · "
                f"[2026 AGM Presentation and Addresses, 28 Oct 2026, PDF pp. 5–6]({AGM_PRESENTATION})"
            )
        st.caption("Independent analysis of historical disclosures. HospitIQ is unaffiliated with SiteMinder.")
