from typing import TypeVar

InstanceType = TypeVar('InstanceType')

class FilterHandler:

    @classmethod
    def filter_instances(cls,
                         instances: list[InstanceType],
                         **criteria) -> list[InstanceType]:
        """
        Filters instances based on dynamic criteria.

        Subclasses can define _filter_by_<criterion> methods to influence filtering.
        """

        if not criteria:
            raise ValueError("At least one filtering criterion must be provided.")

        def filt(inst: InstanceType) -> bool:
            for criterion, value in criteria.items():
                if value is None:
                    # If the value is None, ignore the criterion
                    continue
                method_name = f'_filter_by_{criterion}'
                for c in inst.__class__.__mro__:
                    if hasattr(c, method_name):
                        method = getattr(c, method_name)
                        if not method(inst, value):
                            return False
                        break
                else:
                    # If no method is found for the criterion, skip this instance
                    return False
            return True

        return list(filter(filt, instances))
