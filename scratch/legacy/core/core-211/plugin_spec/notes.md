Using `pluggy` was a good exercise for understanding the complexities of implementing and using a plugin manager.  However, it was ultimately rejected b/c it lacked explicit handler prioritization and was difficult to manage overlapping plugin responsibility domains.  

The `task handler` flexible MRO pipeline was introduced in v3+ to replace this.