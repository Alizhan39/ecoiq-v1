//! Offline, non-production CLI for cross-language contract tests.
//! Usage: cargo run --offline -- --input 1000 --loss 120 --unit kg --period 2026-10
//! Use `unknown` for an absent value. Output JSON contains NO input evidence.
use ecoiq_resource_kernel::{reported_loss_rate, ReportedFlow};
use std::env;
use std::process::ExitCode;

fn read_quantity(raw: &str) -> Result<Option<f64>, &'static str> {
    if raw == "unknown" {
        return Ok(None);
    }
    if raw.trim().is_empty() || raw.len() > 40 {
        return Err("bad quantity");
    }
    let parsed: f64 = raw.parse().map_err(|_| "bad quantity")?;
    if !parsed.is_finite() || parsed < 0.0 {
        return Err("bad quantity");
    }
    Ok(Some(parsed))
}

fn run(args: &[String]) -> Result<String, &'static str> {
    if args.len() != 8
        || args[0] != "--input" || args[2] != "--loss"
        || args[4] != "--unit" || args[6] != "--period"
    {
        return Err("usage: --input VALUE --loss VALUE --unit UNIT --period YYYY-MM");
    }
    let input = read_quantity(&args[1])?;
    let loss = read_quantity(&args[3])?;
    let unit = &args[5];
    let period = &args[7];
    if unit.len() > 32 || period.len() != 7
        || !period.as_bytes().get(4).is_some_and(|char| *char == b'-')
        || !period[..4].bytes().all(|c| c.is_ascii_digit())
        || !period[5..].bytes().all(|c| c.is_ascii_digit())
    {
        return Err("invalid unit or period");
    }
    let month: u8 = period[5..].parse().map_err(|_| "invalid month")?;
    if !(1..=12).contains(&month) {
        return Err("invalid month");
    }
    let result = reported_loss_rate(&ReportedFlow { input, loss, unit, period })
        .map_err(|_| "invalid reported flow")?;
    let output = match result.percent {
        Some(value) => format!(
            "{{\"status\":\"{}\",\"loss_percent\":{value:.10},\"independently_verified\":false,\"implementation_permitted\":false}}",
            result.status
        ),
        None => format!(
            "{{\"status\":\"{}\",\"loss_percent\":null,\"independently_verified\":false,\"implementation_permitted\":false}}",
            result.status
        ),
    };
    Ok(output)
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    match run(&args) {
        Ok(result) => {
            println!("{result}");
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("EcoIQ native candidate rejected input: {message}");
            ExitCode::FAILURE
        }
    }
}
