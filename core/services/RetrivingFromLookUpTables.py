# utils.py or lookup_utils.py


class RetrievingFromLookupTables:
    """
    Utility class for retrieving values from lookup tables like ReceiptCategory.
    Uses class-level caching to reduce DB hits.
    """

    _category_cache = {}
    _kind_cache = {}
    _type_cache = {}
    _name_cache = {}

    @classmethod
    def get_category_name_by_id(cls, category_id):
        if category_id in cls._category_cache:
            return cls._category_cache[category_id]

        try:
            from core.models.look_up_tables import (
                ReceiptCatagory,
            )  # Note: typo in model name?

            name = (
                ReceiptCatagory.objects.filter(id=category_id)
                .values_list("name", flat=True)
                .first()
            )
            cls._category_cache[category_id] = name
            return name
        except Exception as e:
            print(f"Error fetching category name for ID {category_id}: {e}")
            cls._category_cache[category_id] = None
            return None

    @classmethod
    def get_kind_name_by_id(cls, kind_id):
        if kind_id in cls._kind_cache:
            return cls._kind_cache[kind_id]

        try:
            from core.models.look_up_tables import ReceiptKind

            name = (
                ReceiptKind.objects.filter(id=kind_id)
                .values_list("name", flat=True)
                .first()
            )
            cls._kind_cache[kind_id] = name
            return name
        except Exception as e:
            print(f"Error fetching kind name for ID {kind_id}: {e}")
            cls._kind_cache[kind_id] = None
            return None

    @classmethod
    def get_type_name_by_id(cls, type_id):
        if type_id in cls._type_cache:
            return cls._type_cache[type_id]

        try:
            from core.models.look_up_tables import ReceiptType

            name = (
                ReceiptType.objects.filter(id=type_id)
                .values_list("name", flat=True)
                .first()
            )
            cls._type_cache[type_id] = name
            return name
        except Exception as e:
            print(f"Error fetching type name for ID {type_id}: {e}")
            cls._type_cache[type_id] = None
            return None

    @classmethod
    def get_name_name_by_id(cls, name_id):  # Or call it get_receipt_name_by_id
        if name_id in cls._name_cache:
            return cls._name_cache[name_id]

        try:
            from core.models.look_up_tables import ReceiptName

            name = (
                ReceiptName.objects.filter(id=name_id)
                .values_list("name", flat=True)
                .first()
            )
            cls._name_cache[name_id] = name
            return name
        except Exception as e:
            print(f"Error fetching receipt name (template) for ID {name_id}: {e}")
            cls._name_cache[name_id] = None
            return None
