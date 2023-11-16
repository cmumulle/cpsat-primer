"""
This file runs the actual benchmark on the instances.
"""


import logging
# for saving the results easily
from algbench import Benchmark  # pip install algbench

# for distributing the benchmark on a cluster
import slurminade  # pip install slurminade
from _utils import GraphInstanceDb
from _conf import INSTANCE_DB, EXPERIMENT_DATA, TIME_LIMIT, STRATEGIES, OPTIMALITY_TOLERANCES

instances = GraphInstanceDb(INSTANCE_DB)
benchmark = Benchmark(EXPERIMENT_DATA)

# -----------------------------------------
# Distribution configuration for Slurm
# If you don't have Slurm, this won't do anything.
# If you have slurm, you have to update the configuration to your needs.
slurminade.update_default_configuration(
    partition="alg",
    constraint="alggen03",
    mail_user="my_mail@supermail.com",
    mail_type="ALL",  # or "FAIL" if you only want to be notified about failures.
)
slurminade.set_dispatch_limit(1_000)
# -----------------------------------------



@slurminade.slurmify()  # makes the function distributable on a cluster
def load_instance_and_run_solver(instance_name):
    instance = instances[instance_name]
    logger = logging.getLogger("Evaluation")
    benchmark.capture_logger("Evaluation", logging.INFO)

    def run_solver(instance_name, time_limit, strategy, opt_tol, _instance):
        # Arguments starting with _ are not saved in the experiment data.
        # The instance is already in the instance database.
        # We only need the instance name to compare the results.

        solver = STRATEGIES[strategy](_instance, logger=logger)
        obj, lb = solver.solve(time_limit, opt_tol)
        return {
            "num_nodes": _instance.number_of_nodes(),
            "lower_bound": lb,
            "objective": obj,
        }

    # Will only run if the instance is not already solved.
    for strategy in STRATEGIES:
        for opt_tol in OPTIMALITY_TOLERANCES:
            benchmark.add(run_solver, instance_name, TIME_LIMIT, strategy, opt_tol, instance)


# --------------------------
# Compression is not thread-safe so we make it a separate function
# if you only notify about failures, you may want to do
# ``@slurminade.slurmify(mail_type="ALL)`` to be notified after completion.
@slurminade.slurmify()
def compress():
    benchmark.compress()


# --------------------------

# Run the benchmark on all instances.
if __name__ == "__main__":
    job_ids = []
    for instance_name in instances:
        job_ids.append(load_instance_and_run_solver.distribute(instance_name))
    # compress the results at the end.
    compress.wait_for(job_ids).distribute()
