import pandas as pd
pd.set_option('future.no_silent_downcasting', True)

from .base import BaseStrategy
from .config import BacktestConfig
from .registry import STRATEGY_REGISTRY, get_strategy, get_strategy_class, register_strategy
from .utils import fast_supertrend_dir

# Import subclasses to trigger registration
from . import strategy_1
from . import strategy_2
from . import strategy_3
from . import strategy_4
from . import strategy_5
from . import strategy_6
from . import strategy_7
from . import strategy_8
from . import strategy_9
from . import strategy_btst
from . import strategy_10
from . import strategy_11
from . import strategy_12
from . import strategy_13
from . import strategy_14
from . import strategy_15
from . import strategy_16
from . import strategy_17
from . import strategy_18
from . import strategy_19
from . import strategy_20
