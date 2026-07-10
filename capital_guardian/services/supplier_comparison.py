"""
capital_guardian/services/supplier_comparison.py — Phase 3 Supplier
Comparison. `SupplierProfile` rows are a project-independent reference
catalog (see models.py's docstring on the synthetic rating fields); this
service's only real, non-fabricated job is cross-referencing which actual
EquipmentSpec rows (across any project) used a given supplier name — a real
join over already-stored data, not another synthetic figure.
"""
from gold_intelligence.models import EquipmentSpec


def equipment_using_supplier(supplier_name):
    """Real EquipmentSpec rows (any project) whose manufacturer matches this
    supplier's name — a genuine cross-reference, not a fabricated count."""
    return EquipmentSpec.objects.filter(manufacturer__iexact=supplier_name).select_related('project')
