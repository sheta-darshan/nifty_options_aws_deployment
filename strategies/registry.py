STRATEGY_REGISTRY = {}

def register_strategy(cls):
    STRATEGY_REGISTRY[cls.name] = cls
    return cls

def get_strategy_class(name: str):
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Strategy '{name}' not found in registry. Available strategies: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name]

def get_strategy(name: str, params: dict = None):
    cls = get_strategy_class(name)
    return cls(params)
