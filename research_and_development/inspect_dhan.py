import dhanhq
print(f"dhanhq module: {dhanhq}")
print(f"dhanhq type: {type(dhanhq.dhanhq)}")
from dhanhq import dhanhq
print(f"dhanhq class: {dhanhq}")
import inspect
print(f"dhanhq.__init__ signature: {inspect.signature(dhanhq.__init__)}")
