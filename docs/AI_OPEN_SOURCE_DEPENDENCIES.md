# AI open-source dependencies

Direct runtime components introduced for the current non-learned engine are NumPy (BSD-3-Clause), Pillow (HPND), PyYAML (MIT), Pydantic (MIT), and HTTPX (BSD-3-Clause). Existing backend components include FastAPI (MIT), SQLAlchemy (MIT), and cryptography (Apache-2.0/BSD dual licensing). Confirm notices against exact locked distributions during release packaging.

PyTorch (BSD), torchvision (BSD), MONAI (Apache-2.0), OpenCV (Apache-2.0), pydicom (MIT), and ONNX Runtime (MIT) are documented future candidates and are **not installed or used** in the current runtime. Ultralytics and proprietary inference APIs are not dependencies.
