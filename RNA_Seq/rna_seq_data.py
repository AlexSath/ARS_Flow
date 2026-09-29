import warnings
from types import NoneType
import os
from os import PathLike
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import seaborn as sns  # noqa: F401  (registers the "rocket_r" colormap)
from adjustText import adjust_text

from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats

class RNASeq_Data():
    def __init__(self, filepath: PathLike, sep: str, index_col_name: str, sample_number_cat_name: NoneType | str, sample_number_cats: NoneType | dict):
        # Data sources
        # If filepath is false, it's not loaded yet.
        self.data_sources = {filepath: False}
        self.index_col_name = index_col_name
        self.df = self._load_csv(filepath, sep, sample_number_cat_name, sample_number_cats)

        # Helper variables for setting up and maintaining comparisons
        self.currently_comparing = False
        self.current_comparison = None
        self.comparison_table = None
        self.dds = None
        self.ds = None
        self.comparison_p = None
        self.comparison_results = None

    def _load_csv(self, filepath, sep, sample_number_cat_name: NoneType | str, sample_number_cats: NoneType | dict, drop_objects: bool=True):
        # NOTE: If drop_objects is True, then anything object column not in the index_col_name will be dropped
        assert os.path.isfile(filepath)
        if not isinstance(filepath, Path): filepath = Path(filepath)
        df = pd.read_csv(filepath, sep=sep)
        # Set index column
        df = df.set_index(self.index_col_name)
        if drop_objects: df = df.drop(columns=list(df.select_dtypes(include=['object']).columns))
        # NOTE: will always drop the first block of column name i.e. 'drop_keep1_keep2_...' --> 'keep1_keep2_...'
        df = df.rename(columns={x: "_".join(x.split("_")[1:]) for x in df.select_dtypes(include=['number']).columns})
        self.data_sources[filepath] = True

        # converting some columns to data indexes if necessary
        # for example, a df could have 6 columns: [n1, c1, n2, c2, n3, c3]
        # maybe [n1, c1, n2, c2] belong to one group while [n3, c3] belong to a second
        # this converts [n3, c3] --> [n1, c1] and merges DFs mith MultiIndex labels
        # TODO: verify this works for assymetric number of n, c for each merge.
        # TODO: either verify this works for >2 categories OR error check to limit to 2 categories
        if sample_number_cats is not None:
            dfs = {}
            for cat, numbers in sample_number_cats.items(): # loop through "cat": [n1, n2, ...]
                cols = [] # for identifying [n3, n4, ...]
                new_cols = [] # for replacing [n3, n4, ...] with [n1, n2, ...]
                for n in numbers: # loop through [n1, n2, ...]
                    for col in df.columns:
                        if str(n) in col: 
                            cols.append(col)
                            new_cols.append(col.replace(str(n), str(np.ceil(len(cols) / 2).astype(int))))
                dfs[cat] = df[cols]
                dfs[cat].columns = new_cols
            
            # DFs should now be split in 'dfs'
            df = pd.concat(dfs.values(), keys=dfs.keys(), names=[sample_number_cat_name, df.index.name])
            df = df.reorder_levels(df.index.names[::-1])

        # return DF
        return df
    
    def add_csv(self, filepath: PathLike, sep: str, sample_number_cat_name: NoneType | str, sample_number_cats: NoneType | dict, category_name, old_data_category, new_data_category, drop_objects: bool=True):
        """
        Description: Will add a new df from a new filepath, and create a new column to distinguish
        between old and new data.

        NOTE: For all index columns, the same unique values must be present for old and new data
        for the proper merge to occur.

        Args:
        - category_name: name of the new column with categories separating old and new data
        - old_data_category: name of the category that old data will be filled with in the new column
        - new_data_category: name of the category that the new data will be filled with the new column
        """
        # TODO: add error checking for if indexes don't match between original and new df
        # TODO: decide whether to allow more than 2x2x2x... for each MultiIndex level. If 2x2 is maintained, then heatmaps always possible. If NxM categories allowed, then merging and heatmaps become trickier.
        add_df = self._load_csv(
            filepath, sep, 
            sample_number_cat_name=sample_number_cat_name, sample_number_cats=sample_number_cats,
            drop_objects=drop_objects
        )
        assert np.all(add_df.index == self.df.index), f"DF index must match, but {add_df.index} and {self.df.index} do not!"
        self.df = pd.concat(
            [self.df, add_df], keys=[old_data_category, new_data_category], 
            names=[category_name] + self.df.index.names
        )
        self.df = self.df.reorder_levels(
            self.df.index.names[1:] + [self.df.index.names[0]]
        )

    def _setup_comparison_table(self, index_level_name, filters: NoneType | dict):
        """
        Sets up comparison pivot table.

        Arg:
        - index_level_name: name of the MultiIndex level that will be used to index the pivot comparison table
        - filters: for other indexes, filter to limit the number of variables to 2.
        """
        # Validating inputs
        EXPECTED = 2
        if self.currently_comparing: raise ValueError(f"Already comparing {self.current_comparison}. Close current comparison before starting a new one!")
        this_index_level_n_unique = len(self.df.index.get_level_values(index_level_name).unique())
        assert this_index_level_n_unique == EXPECTED, f"Expected {EXPECTED} unique values in MultiIndex level {index_level_name}, got {this_index_level_n_unique}."
        if filters is not None:
            assert len(self.df.index.names) == len(filters) + 2, \
                f"DF MultiIndex has {len(self.df.index.names)} levels. Expected a filter of size {len(self.df.index.names) - 2}, but got {len(filters)}"

        # Creating MultiIndex based on filters
        for key in filters.keys(): assert key >= 0 and key < len(self.df.index.names), f"Filter key {key} not a valid level in DF MultiIndex."
        filter_slice = tuple(filters[idx] if idx in filters.keys() else slice(None) for idx in np.arange(len(self.df.index.names)))

        # Creating pivot table
        self.comparison_table = pd.pivot_table(
            data=self.df.loc[filter_slice,:],
            columns=index_level_name,
            values=self.df.columns,
            index=self.index_col_name,
        )
        self.currently_comparing = True
        self.current_comparison = [index_level_name, filters]
        
    # ---------------------------------------------------------------------------
    # _calculate_comparison_p_values
    # ---------------------------------------------------------------------------
    def _calculate_comparison_p_values(self, n_cpus: int = 8, alpha: float = 0.05):
        assert self.currently_comparing, "Must start comparing before calculating p-values!"
        level = self.current_comparison[0]

        count_cols = [c for c in self.comparison_table.columns.get_level_values(0).unique() if "count" in c]
        p_table = self.comparison_table.loc[:, count_cols].T  # rows: (replicate_col, condition), cols: genes

        # Traceable sample IDs instead of a bare RangeIndex, e.g. "1_count|Ctrl"
        sample_ids = ["|".join(map(str, t)) for t in p_table.index]
        metadata_table = pd.DataFrame({level: p_table.index.get_level_values(level)}, index=sample_ids)
        p_table.index = sample_ids

        # Round, don't truncate: astype(int) turns 0.9 into 0 and biases every gene downward.
        p_table = p_table.round().astype(int)

        inference = DefaultInference(n_cpus=n_cpus)
        self.dds = DeseqDataSet(
            counts=p_table,
            metadata=metadata_table,
            design=f"~{level}",
            refit_cooks=True,
            inference=inference,
        )
        # Runs the canonical sequence, including fit_MAP_dispersions (dispersion shrinkage),
        # which the manual step list skipped.
        self.dds.deseq2()

        # Reference level = alphabetically first condition unless you set ref_level,
        # so [0, 1] is (second condition) vs (first condition).
        self.ds = DeseqStats(
            self.dds,
            contrast=np.array([0, 1]),
            alpha=alpha,
            cooks_filter=True,
            independent_filter=True,
            inference=inference,
        )
        # summary() is where Cook's filtering, independent filtering, and BH adjustment
        # actually happen. run_wald_test() alone gives raw, unfiltered p-values.
        self.ds.summary()
        self.comparison_results = self.ds.results_df  # baseMean, log2FoldChange, lfcSE, stat, pvalue, padj
        self.comparison_p = self.comparison_results["pvalue"].sort_values()

    def plot_comparison_density(
        self,
        ax=None,
        x_cond=None,
        y_cond=None,
        top_n: int | None = None,
        genes=None,
        p_threshold: float | None = None,
        highlight_color: str | None = "k",
        p_col: str = "padj",
        value_key: str = "cpm",
        pseudocount: float | None = None,
        min_log: float = -1.0,
        bins: int = 100,
        norm=None,
        cmap=None,
        colorbar: bool = True,
        title: str | None = None,
        label_fontsize: int = 8,
        max_labels: int = 50,
    ):
        """
        2D density of log10(mean CPM) for the current comparison, with genes highlighted by p-value.

        Highlight modes (mutually exclusive; none = no highlights):
        - top_n:       the N genes with the lowest `p_col`
        - p_threshold: all genes with `p_col` <= threshold (labels capped at `max_labels`)
        - genes:       an explicit list of gene names; their p-values are shown in the labels

        Args:
        - ax: existing Axes to draw into (for multi-panel figures). If None, a new figure is made.
        - x_cond, y_cond: condition labels for the axes. Default: alphabetical order, which
        matches the DESeq2 reference level used in _calculate_comparison_p_values.
        - p_col: "padj" (recommended) or "pvalue".
        - pseudocount: if None, genes with 0 CPM in either condition are dropped (log10(0) = -inf),
        matching the original plot. Set e.g. 0.1 to keep them at the lower edge.
        - norm: pass a shared mcolors.LogNorm(vmin=1, vmax=...) to make colors comparable across panels.

        Returns: (ax, highlighted) where `highlighted` is a DataFrame of the labeled genes.
        """
        if not self.currently_comparing:
            raise ValueError("Start a comparison (_setup_comparison_table) before plotting.")
        if self.comparison_results is None:
            raise ValueError("Run _calculate_comparison_p_values() before plotting.")
        if sum(v is not None for v in (top_n, genes, p_threshold)) > 1:
            raise ValueError("Use only one of top_n, genes, p_threshold.")
        res = self.comparison_results
        if p_col not in res.columns:
            raise ValueError(f"p_col must be one of {list(res.columns)}, got {p_col!r}.")

        level, filters = self.current_comparison

        # --- Mean expression per condition across replicates ---
        tbl = self.comparison_table
        val_cols = [c for c in tbl.columns.get_level_values(0).unique() if value_key in c]
        if not val_cols:
            raise ValueError(f"No columns containing {value_key!r} in the comparison table.")
        expr = tbl.loc[:, val_cols].T.groupby(level=level).mean().T  # index: genes, cols: conditions

        conds = sorted(expr.columns)
        if len(conds) != 2:
            raise ValueError(f"Expected 2 conditions in level {level!r}, got {conds}.")
        x_cond = x_cond if x_cond is not None else conds[0]
        y_cond = y_cond if y_cond is not None else conds[1]

        # --- Log transform ---
        pc = 0.0 if pseudocount is None else pseudocount
        with np.errstate(divide="ignore"):
            plot_df = pd.DataFrame({
                "x": np.log10(expr[x_cond] + pc),
                "y": np.log10(expr[y_cond] + pc),
            })
        plot_df = plot_df.replace([np.inf, -np.inf], np.nan).dropna()
        plot_df = plot_df[(plot_df["x"] >= min_log) & (plot_df["y"] >= min_log)]

        # --- Select genes to highlight ---
        pvals = res[p_col]
        if top_n is not None:
            sel = pvals.dropna().nsmallest(top_n).index
        elif p_threshold is not None:
            sel = pvals[pvals <= p_threshold].sort_values().index
        elif genes is not None:
            sel = pd.Index(list(genes))
        else:
            sel = pd.Index([])

        not_in_results = sel.difference(res.index)
        if len(not_in_results):
            warnings.warn(f"Not in DESeq2 results: {list(not_in_results)}")
        not_plotted = sel.intersection(res.index).difference(plot_df.index)
        if len(not_plotted):
            warnings.warn(
                f"{len(not_plotted)} highlighted gene(s) fall outside the plotted range "
                f"(zero CPM or below min_log): {list(not_plotted)}. Consider setting pseudocount."
            )

        highlighted = plot_df.reindex(sel).dropna()
        highlighted[p_col] = pvals.reindex(highlighted.index)
        highlighted = highlighted.sort_values(p_col, na_position="last")
        labeled = highlighted.head(max_labels)
        if len(highlighted) > max_labels:
            warnings.warn(f"{len(highlighted)} genes highlighted; labeling only the {max_labels} lowest {p_col}.")

        # --- Plot ---
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 5.5), layout="constrained")
        else:
            fig = ax.figure

        if cmap is None:
            cmap = mpl.colormaps["rocket_r"].copy()  # copy so the global registry isn't modified
            cmap.set_bad(alpha=0)
        if norm is None:
            norm = mcolors.LogNorm()

        hi = float(np.ceil(max(plot_df["x"].max(), plot_df["y"].max()) * 10) / 10)
        lims = (min_log, hi)
        _, _, _, im = ax.hist2d(
            plot_df["x"], plot_df["y"],
            bins=bins, range=[lims, lims],
            cmap=cmap, norm=norm, cmin=1,
        )
        ax.scatter(highlighted["x"], highlighted["y"], color=highlight_color, s=12, zorder=3)
        if colorbar:
            fig.colorbar(im, ax=ax, label="genes per bin")
        ax.axline((0, 0), slope=1, color="0.5", lw=1, ls="--")
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ax.set_aspect("equal")

        texts = []
        for gene, row in labeled.iterrows():
            p = row[p_col]
            if pd.isna(p): p_str = f"{gene} NA"
            elif p >= 0.05: p_str = f"{gene} NS"
            elif p == 0: p_str = f"{gene} p=0"
            else: p_str = f"{gene} p={p:.0e}"
            # p_str = "NA" if pd.isna(p) else f"{p:.0e}"
            texts.append(ax.text(
                row["x"], row["y"], p_str, fontsize=label_fontsize,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")],
            ))

        if texts:
            fig.canvas.draw()  # finalize layout (aspect, colorbar) before adjusting
            adjust_text(
                texts,
                x=highlighted["x"].to_numpy(), y=highlighted["y"].to_numpy(),  # points to avoid
                ax=ax, expand=(1.2, 1.4),
                arrowprops=dict(arrowstyle="-", color="0.3", lw=0.5),
            )

        ax.set_xlabel(f"log10 CPM ({x_cond})")
        ax.set_ylabel(f"log10 CPM ({y_cond})")
        if title is None:
            context = " ".join(str(v) for v in filters.values()) if filters else ""
            if top_n is not None:
                desc = f"{top_n} lowest {p_col} highlighted"
            elif p_threshold is not None:
                desc = f"{p_col} \u2264 {p_threshold:g} highlighted"
            elif genes is not None:
                desc = "selected genes highlighted"
            else:
                desc = ""
            title = f"{context} log10(CPM): {y_cond} vs {x_cond}".strip() + (f"\n{desc}" if desc else "")
        ax.set_title(title)

        return ax, highlighted
    
    # ---------------------------------------------------------------------------
    # 3) close_comparison (needed to loop over comparisons for multi-panel figures)
    # ---------------------------------------------------------------------------
    def close_comparison(self):
        self.currently_comparing = False
        self.current_comparison = None
        self.comparison_table = None
        self.dds = None
        self.ds = None
        self.comparison_p = None
        self.comparison_results = None

    def head(self):
        return self.df.head()

    def info(self):
        print(f"{'Dataframe ID: ':<20}{self.base_id:>10}")
        print(f"{'Dataframe Rows: ':<20}{self.df.shape[0]:>10}")
        print(f"{'Dataframe Columns: ':<20}{self.df.shape[1]:>10}")
        print(f"{'Number of Samples: ':<20}{self.n_samples:>10}\n")
        print(f"{'Sample name: ':<20}{'Col Index':>10}")
        for idx in range(len(self.sample_names)):
            print(f"{self.sample_names[idx]:<20}{self.sample_col_indexes[idx]:>10}")


# ---------------------------------------------------------------------------
# Attach to the class (or paste the functions in as methods)
# ---------------------------------------------------------------------------
# RNASeq_Data._calculate_comparison_p_values = _calculate_comparison_p_values
# RNASeq_Data.close_comparison = close_comparison
# RNASeq_Data.plot_comparison_density = plot_comparison_density


