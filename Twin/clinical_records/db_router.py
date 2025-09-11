class ClinicalRecordsRouter:
    """Router to control database operations on models for clinical records."""

    db_name = "clinical_records"
    route_app_labels = {"clinical_records"}

    def db_for_read(self, model, **hints):
        """Point all read operations for clinical record models to the dedicated DB."""
        return self.db_name if model._meta.app_label in self.route_app_labels else None

    def db_for_write(self, model, **hints):
        """Prevent all write operations to clinical_records."""
        if model._meta.app_label in self.route_app_labels:
            return None  # No write routing for read-only DB
        return None  # Allow default routing for other apps

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations within or between clinical_records and other apps."""
        app_label_1 = obj1._meta.app_label
        app_label_2 = obj2._meta.app_label

        if (
            app_label_1 in self.route_app_labels
            and app_label_2 in self.route_app_labels
        ):
            return True
        if app_label_1 in self.route_app_labels or app_label_2 in self.route_app_labels:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Prevent migrations on clinical_records DB."""
        if app_label == "clinical_records":
            return False
        return None
