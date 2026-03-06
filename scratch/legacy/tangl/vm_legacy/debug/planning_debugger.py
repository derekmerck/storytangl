"""Utilities for printing provisioning offer audits during development."""

from __future__ import annotations

from typing import Iterable

from tangl.vm.provision import PlanningReceipt, ProvisionOffer


class PlanningDebugger:
    """Pretty-printers for planning receipts and competing offers."""

    @staticmethod
    def print_receipt(receipt: PlanningReceipt) -> None:
        """Print a human-readable summary of a :class:`PlanningReceipt`."""

        header = f"Planning Receipt @ cursor {receipt.cursor_id}"
        print(f"\n{header}\n{'=' * len(header)}")
        print(f"Frontier nodes: {len(receipt.frontier_node_ids)}")
        if receipt.softlock_detected:
            print("Status     : SOFTLOCK detected")
        else:
            print("Status     : OK")
        print(f"Builds     : {len(receipt.builds)} accepted")
        print(f"Unresolved : {len(receipt.unresolved_hard_requirements)} hard")
        print(f"Waived     : {len(receipt.waived_soft_requirements)} soft")

        if not receipt.selection_audit:
            print("No selection audit recorded.")
            return

        print("\nSelections")
        print("-----------")
        for entry in receipt.selection_audit:
            label = entry.get("requirement_label") or entry.get("requirement_uid")
            node_label = entry.get("node_label")
            print(
                f"Requirement {label} (node={node_label}): {entry.get('reason')}\n"
                f"  offers={entry.get('num_offers')} selected_cost={entry.get('selected_cost')}"
            )
            for idx, offer in enumerate(entry.get("all_offers", []), start=1):
                marker = "*" if offer.get("cost") == entry.get("selected_cost") else " "
                detail = offer.get("proximity_detail") or offer.get("proximity")
                print(
                    f"    {marker}{idx}. op={offer.get('operation')} cost={offer.get('cost')}"
                    f" proximity={detail} provider={offer.get('provider_id')}"
                )

    @staticmethod
    def compare_offers(offers: Iterable[ProvisionOffer]) -> None:
        """Print competing offers side-by-side for quick inspection."""

        offers = sorted(offers, key=lambda offer: offer.get_sort_key())
        print("\nOffer Comparison\n-----------------")
        print(f"{'Provider':<38} {'Cost':<10} {'Proximity':<15} Operation")
        for offer in offers:
            provider = getattr(offer, "provider_id", None)
            provider_id = str(provider)[:36] if provider else "<new>"
            proximity_detail = offer.proximity_detail or offer.proximity
            print(
                f"{provider_id:<38} {offer.cost:<10.1f} {str(proximity_detail):<15}"
                f" {_policy_from_offer(offer).name}"
            )


def _policy_from_offer(offer: ProvisionOffer):
    """Helper mirroring :func:`tangl.vm.provision.resolver._policy_from_offer`."""

    from tangl.vm.provision.resolver import _policy_from_offer as resolver_policy

    return resolver_policy(offer)
