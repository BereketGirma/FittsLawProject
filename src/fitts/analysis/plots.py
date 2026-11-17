"""Offline plotting only; the task UI does not import analysis dependencies."""


def plot_conditions(conditions, directions, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(8, 5))
    for direction, group in conditions.groupby("direction"):
        axis.scatter(group.index_of_difficulty, group.mean_movement_time_ms, label=direction)
    axis.set(xlabel="Shannon index of difficulty (bits)", ylabel="Mean movement time (ms)")
    axis.legend()
    fig.tight_layout()
    fig.savefig(output / "movement_time_vs_difficulty.png", dpi=180)
    plt.close(fig)
    fig, axis = plt.subplots(figsize=(6, 4))
    axis.bar(directions.direction, directions.mean_movement_time_ms)
    axis.set(ylabel="Mean movement time (ms)", xlabel="Movement direction")
    fig.tight_layout()
    fig.savefig(output / "left_vs_right.png", dpi=180)
    plt.close(fig)
