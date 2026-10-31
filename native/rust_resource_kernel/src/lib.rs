//! Candidate numeric kernel for *reported* resource measurements.
//!
//! Deliberately separate from the authoritative Python EcoIQ OS.
//! Not a finance engine (f64 is unsuitable for money), causal inference,
//! religious score, independently verified evidence or Islah approval.

#[derive(Debug, PartialEq)]
pub enum MeasurementError {
    MissingUnit,
    MissingPeriod,
    NonFinite,
    NegativeQuantity,
    LossGreaterThanInput,
    ZeroDenominatorWithLoss,
}

#[derive(Clone, Debug)]
pub struct ReportedFlow<'a> {
    pub input: Option<f64>,
    pub loss: Option<f64>,
    pub unit: &'a str,
    pub period: &'a str,
}

#[derive(Debug, PartialEq)]
pub struct ReportedLoss {
    pub percent: Option<f64>,
    pub status: &'static str,
    pub independently_verified: bool,
    pub implementation_permitted: bool,
}

pub fn reported_loss_rate(flow: &ReportedFlow<'_>) -> Result<ReportedLoss, MeasurementError> {
    if flow.unit.trim().is_empty() {
        return Err(MeasurementError::MissingUnit);
    }
    if flow.period.trim().is_empty() {
        return Err(MeasurementError::MissingPeriod);
    }
    for value in [flow.input, flow.loss].into_iter().flatten() {
        if !value.is_finite() {
            return Err(MeasurementError::NonFinite);
        }
        if value < 0.0 {
            return Err(MeasurementError::NegativeQuantity);
        }
    }
    let percent = match (flow.input, flow.loss) {
        (Some(total), Some(loss)) => {
            if loss > total {
                return Err(MeasurementError::LossGreaterThanInput);
            }
            if total == 0.0 {
                if loss > 0.0 {
                    return Err(MeasurementError::ZeroDenominatorWithLoss);
                }
                None // Cannot define 0/0 as zero loss rate.
            } else {
                Some((loss / total) * 100.0)
            }
        }
        _ => None, // Unknown stays unknown, NEVER imputed to 0.
    };
    Ok(ReportedLoss {
        percent,
        status: if percent.is_some() {
            "CALCULATED_FROM_REPORTED_INPUTS"
        } else {
            "INSUFFICIENT_DATA"
        },
        independently_verified: false,
        implementation_permitted: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample(input: Option<f64>, loss: Option<f64>) -> ReportedFlow<'static> {
        ReportedFlow { input, loss, unit: "kg", period: "2026-10" }
    }

    #[test]
    fn reported_twelve_percent_is_neither_verified_nor_approved() {
        let result = reported_loss_rate(&sample(Some(1000.0), Some(120.0))).unwrap();
        assert_eq!(result.percent, Some(12.0));
        assert!(!result.independently_verified);
        assert!(!result.implementation_permitted);
    }

    #[test]
    fn missing_is_not_measured_zero() {
        let missing = reported_loss_rate(&sample(Some(1000.0), None)).unwrap();
        let zero = reported_loss_rate(&sample(Some(1000.0), Some(0.0))).unwrap();
        assert_eq!(missing.percent, None);
        assert_eq!(missing.status, "INSUFFICIENT_DATA");
        assert_eq!(zero.percent, Some(0.0));
    }

    #[test]
    fn zero_denominator_is_unknown_not_zero_percent() {
        let result = reported_loss_rate(&sample(Some(0.0), Some(0.0))).unwrap();
        assert_eq!(result.percent, None);
    }

    #[test]
    fn rejects_invalid_inputs() {
        for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY, -1.0] {
            assert!(reported_loss_rate(&sample(Some(value), Some(0.0))).is_err());
        }
        assert_eq!(
            reported_loss_rate(&sample(Some(10.0), Some(11.0))).unwrap_err(),
            MeasurementError::LossGreaterThanInput,
        );
        assert_eq!(
            reported_loss_rate(&ReportedFlow {
                input: Some(10.0), loss: Some(2.0), unit: "", period: "2026-10"
            }).unwrap_err(),
            MeasurementError::MissingUnit,
        );
    }

    #[test]
    fn unknown_input_prevents_calculation() {
        assert_eq!(reported_loss_rate(&sample(None, Some(0.0))).unwrap().percent, None);
    }
}
