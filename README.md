# research-project-jerzy

## Description

This repository contains code and simulations for a research project exploring quantum network protocols using [SquidASM](https://squidasm.readthedocs.io/en/latest/index.html), a simulator for quantum networking built on NetSquid. The project uses **Python 3.12.7** and is compatible with **SquidASM version 0.13.4**.

## Installation

### Requirements

- Python 3.12.7
- SquidASM 0.13.4

### Setup

1. Clone the repository:
   ```bash
   git clone https://gitlab.tudelft.nl/2425-cse3000-byzantine/research-project-jerzy.git
   cd research-project-jerzy
   ```

2. Install **SquidASM** by following the official installation guide:  
   👉 [SquidASM Installation Guide](https://squidasm.readthedocs.io/en/latest/index.html)

## Usage

After installation, run simulation scripts using:
```bash
python simulation_script.py
```

Replace `simulation_script.py` with the actual filename containing your simulation or experiment logic.

## Project Structure

```
research-project-jerzy/
│
├── no_faulty/               # Simulation with no faulty nodes
│   ├── application.py
│   ├── run_simulation.py
│   ├── run_noisy_simulation.py
│   ├── no_faulty_1000.png
│   └── no_faulty_noise_1000.png
│
├── node1_faulty/            # Simulation with R0 as faulty
│   ├── application.py
│   ├── run_simulation.py
│   ├── run_noisy_simulation.py
│   ├── node1_faulty_1000.png
│   └── node1_faulty_noise_1000.png
│
├── sender_faulty/           # Simulation with sender as faulty
│   ├── application.py
│   ├── run_simulation.py
│   ├── run_noisy_simulation.py
│   ├── sender_faulty_1000.png
│   └── sender_faulty_noise_1000.png
│
├── config.yaml              # Shared simulation config
├── .gitignore
└── README.md

```

## Contributing

Contributions are welcome. Please ensure:

- Code is well-documented
- Changes are tested
- Pull requests include a clear explanation

## Authors and Acknowledgment

Developed as part of the CSE3000 Research Project at TU Delft. Thanks to the SquidASM developers for the simulation platform.

## License

This project is for academic and research purposes. Licensing to be determined.

## Project Status

✅ Skeleton for simulation is ready.  
🧵 Further investigation into multithreading support is required.
