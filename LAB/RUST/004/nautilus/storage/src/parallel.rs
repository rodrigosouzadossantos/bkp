use rayon::prelude::*;

pub fn parallel_map<T, R, F>(
    data: Vec<T>,
    f: F,
) -> Vec<R>
where
    T: Send,
    R: Send,
    F: Fn(T) -> R + Send + Sync,
{
    data.into_par_iter().map(f).collect()
}
