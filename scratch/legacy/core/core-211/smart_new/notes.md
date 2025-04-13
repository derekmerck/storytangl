The `SmartNew` metaclass and handler was the culmination of the `Automorphic` and `Templated` mixins. 

It is still applicable, but less relevant since v3, as all story-related node creation now goes through the `structure` function, which directly integrates explicit sub-class casting by `obj_cls` using the same mechanisms.