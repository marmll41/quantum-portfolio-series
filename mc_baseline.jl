# Julia port of the plain Monte Carlo baseline (sampler `full`).
#
# Same model (read from model.bin, written by export_model.py), same work
# per path: 100 standard normals, the full 100x100 correlation matmul, the
# dot product with the weights. Same estimator: linear-interpolated quantile
# as in np.quantile, CVaR = mean of losses >= VaR. The only thing that
# changes is the language -- that is the question being asked.
#
# Julia is column-major, so a block is d x k (one path per column) and the
# correlation step is L * Z.
#
# Usage:
#   julia -t 14 mc_baseline.jl N [reps] [block]
#
# BLAS is pinned to one thread; parallelism comes from Julia threads, each
# with its own RNG and its own buffers. Timings exclude JIT compilation
# (one warm-up run first) -- the compile cost is reported separately.

using LinearAlgebra, Random, Statistics, Printf

# Julia ships OpenBLAS; NumPy on macOS links Apple Accelerate. For a
# language comparison both must use the same BLAS:
#   JL_BLAS=accelerate julia --project=<env with AppleAccelerate> ...
if get(ENV, "JL_BLAS", "openblas") == "accelerate"
    using AppleAccelerate
end

function load_model(path = joinpath(@__DIR__, "model.bin"))
    raw = reinterpret(Float64, read(path))
    d = Int(raw[1]); truth = raw[2]
    mu = raw[3:2+d]; w = raw[3+d:2+2d]
    # stored row-major; transpose into Julia's column-major layout
    L = permutedims(reshape(raw[3+2d:2+2d+d*d], d, d))
    return (; d, truth, mu, w, L)
end

function sample_losses!(out, m, seed, block)
    n = length(out)
    wmu = dot(m.w, m.mu)
    nt = Threads.nthreads()
    ranges = [(1 + (t-1)*n ÷ nt):(t*n ÷ nt) for t in 1:nt]
    Threads.@threads :static for t in 1:nt
        rng = Xoshiro(seed + t)
        Z = Matrix{Float64}(undef, m.d, block)
        R = similar(Z)
        l = Vector{Float64}(undef, block)
        r = ranges[t]
        i = first(r)
        while i <= last(r)
            k = min(block, last(r) - i + 1)
            Zv = view(Z, :, 1:k); Rv = view(R, :, 1:k); lv = view(l, 1:k)
            randn!(rng, Zv)
            mul!(Rv, m.L, Zv)              # correlated shocks, d x k
            mul!(lv, transpose(Rv), m.w)   # portfolio return per path
            @inbounds for j in 1:k
                out[i+j-1] = -lv[j] - wmu
            end
            i += k
        end
    end
    return out
end

function cvar(losses, q = 0.99)
    v = quantile!(losses, q)               # same interpolation as numpy
    s = 0.0; c = 0
    @inbounds for x in losses
        if x >= v
            s += x; c += 1
        end
    end
    return s / c
end

function run_once(m, n, seed, block, buf)
    t0 = time_ns()
    sample_losses!(buf, m, seed, block)
    est = cvar(buf)
    return (time_ns() - t0) / 1e9, est
end

function main(args)
    n = parse(Int, args[1])
    reps = length(args) >= 2 ? parse(Int, args[2]) : 20
    block = length(args) >= 3 ? parse(Int, args[3]) : 256
    BLAS.set_num_threads(1)
    m = load_model()
    buf = Vector{Float64}(undef, n)

    tc = @elapsed run_once(m, 1024, 1, block, Vector{Float64}(undef, 1024))
    run_once(m, n, 2, block, buf)          # warm-up at full size

    times = Float64[]; errs = Float64[]
    for r in 1:reps
        dt, est = run_once(m, n, 7 + 1000r, block, buf)
        push!(times, dt); push!(errs, est - m.truth)
    end
    rel = sqrt(mean(errs .^ 2)) / abs(m.truth)
    @printf("julia %s  threads=%d  blas=%s  block=%d  N=%d  reps=%d\n",
            VERSION, Threads.nthreads(), BLAS.get_config().loaded_libs[end].libname |> basename,
            block, n, reps)
    @printf("  first call incl. compile: %.3f s\n", tc)
    @printf("  time median %.2f ms   min %.2f ms   relerr_cvar %.3e   paths/s %.3e\n",
            1e3 * median(times), 1e3 * minimum(times), rel, n / median(times))
    # Optional machine-readable result for the plots: JL_OUT=julia_x.json
    out = get(ENV, "JL_OUT", "")
    if !isempty(out)
        blas = basename(BLAS.get_config().loaded_libs[end].libname)
        open(out, "w") do io
            @printf(io, """{"julia": "%s", "threads": %d, "blas": "%s", "block": %d, "n": %d, "reps": %d, "compile_s": %.4f, "time_median_s": %.6f, "time_min_s": %.6f, "relerr_cvar": %.6e}\n""",
                    VERSION, Threads.nthreads(), blas, block, n, reps, tc,
                    median(times), minimum(times), rel)
        end
    end
end

main(ARGS)
