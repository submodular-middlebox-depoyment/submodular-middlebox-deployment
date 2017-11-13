# MIT License
#
# Copyright (c) 2017 Matthias Rost, Alexander Elvers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__author__ = "Matthias Rost, Alexander Elvers (mrost / aelvers <AT> inet.tu-berlin.de)"

import os

import click

import main
from evaluation import abstract_data_extractor as ade_pkg
from experiments import abstract_experiment_manager as aem_pkg


@click.group()
@click.argument("experiment", type=click.Choice(main.experiments.keys()))
@click.pass_context
def cli(ctx, experiment):
    ctx.obj = main.experiments[experiment]


@cli.command()
@click.option("--output", "-o", required=True, type=click.Path(resolve_path=True))
@click.pass_obj
def generate(exp_main_pkg, output):
    exp_mgr = exp_main_pkg.create_experiment_manager_for_generation()
    exp_mgr.construct_scenarios()

    if os.path.exists(output):
        click.confirm("output file exists. overwrite?", prompt_suffix="")
    aem_pkg.pickle_experiment_manager(exp_mgr, path=output)


@cli.command()
@click.option("--input", "-i", required=True, type=click.Path(exists=True, resolve_path=True))
@click.option("--output", "-o", required=True, type=click.Path(resolve_path=True))
@click.option("--server", "-S", required=True, type=int, help="server id (0 .. number_of_servers - 1)")
@click.option("--number_of_servers", "-s", required=True, type=int, help="number of servers that are available")
@click.option("--number_of_cores", "-c", required=True, type=int, help="number of cores that shall be used")
@click.pass_obj
def execute(exp_main_pkg, input, output, server, number_of_servers, number_of_cores):
    exp_mgr = aem_pkg.unpickle_experiment_manager(path=input)
    if not isinstance(exp_mgr, exp_main_pkg.experiment_manager_class):
        raise click.ClickException(f"type of input experiment manager is {type(exp_mgr).__name__}"
                                   f" but should be {exp_main_pkg.experiment_manager_class.__name__}")

    exp_mgr.execute_scenarios(
        server_number=server,
        number_of_servers=number_of_servers,
        number_of_cores=number_of_cores,
    )

    if os.path.exists(output):
        click.confirm("output file exists. overwrite?", prompt_suffix="")
    aem_pkg.pickle_experiment_manager(exp_mgr, path=output)


@cli.command()
@click.argument("inputs", required=True, nargs=-1, type=click.Path(exists=True, resolve_path=True))
@click.option("--output", "-o", required=True, type=click.Path(resolve_path=True))
@click.pass_obj
def aggregate_results(exp_main_pkg, inputs, output):
    data_extractor = exp_main_pkg.data_extractor_class()

    scenario_keys = set()
    for input in inputs:
        exp_mgr = aem_pkg.unpickle_experiment_manager(path=input)
        if not isinstance(exp_mgr, exp_main_pkg.experiment_manager_class):
            raise click.ClickException(f"type of input experiment manager is {type(exp_mgr).__name__}"
                                       f" but should be {exp_main_pkg.experiment_manager_class.__name__}"
                                       f" (loaded from {input})")

        scenario_keys.update(exp_mgr.scenario_keys)
        data_extractor.extract_data_from_experiment_manager(exp_mgr)

    data_extractor.print_it()

    print("everything went smoothly!")

    if os.path.exists(output):
        click.confirm("output file exists. overwrite?", prompt_suffix="")
    ade_pkg.pickle_data_extractor(data_extractor=data_extractor, path=output)


@cli.command()
@click.option("--input", "-i", required=True, type=click.Path(exists=True, resolve_path=True))
@click.pass_obj
def check_completeness(exp_main_pkg, input):
    data_extractor = ade_pkg.unpickle_data_extractor(path=input)
    if not isinstance(data_extractor, exp_main_pkg.data_extractor_class):
        raise click.ClickException(f"type of input data extractor is {type(data_extractor).__name__}"
                                   f" but should be {exp_main_pkg.data_extractor_class.__name__}")
    data_extractor.check_completeness()


if __name__ == "__main__":
    cli()
