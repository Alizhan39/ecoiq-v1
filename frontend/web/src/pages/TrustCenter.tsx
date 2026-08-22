/**
 * Trust Center.
 *
 * Covers only what can be supported. There is no certification claim on this
 * page because EcoIQ holds no certifications — saying "SOC 2" or "ISO" or
 * "GDPR certified" without the audit behind it is the same category of
 * fabrication as a substituted score, and would be far more consequential.
 *
 * Where a control does not exist yet, the page says so.
 */
export default function TrustCenter() {
  return (
    <div className="trust prose">
      <h1>Trust Center</h1>
      <p>
        How EcoIQ handles evidence, what the AI is allowed to do, and what a
        person has to sign off. Where something is not in place yet, this page
        says so.
      </p>

      <section aria-labelledby="evidence">
        <h2 id="evidence">Evidence and provenance</h2>
        <dl>
          <div>
            <dt>Every value records where it came from</dt>
            <dd>
              Measured, inferred, estimated, modelled, seeded, or legacy —
              recorded per metric, append-only, so an earlier belief stays
              answerable.
            </dd>
          </div>
          <div>
            <dt>Derived values record what they were computed from</dt>
            <dd>
              Not which metrics, but which specific provenance records — so
              history stays pinned to what was actually read.
            </dd>
          </div>
          <div>
            <dt>Seeded and legacy data can never become publishable</dt>
            <dd>
              However much of it exists. Contamination anywhere beneath a value
              disqualifies it, including several layers down.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="uncertainty">
        <h2 id="uncertainty">What uncertainty means here</h2>
        <dl>
          <div>
            <dt>Unknown is never a number</dt>
            <dd>
              A missing value is null. It is not zero, and it is not an average.
              A score of zero means an organisation was assessed at zero.
            </dd>
          </div>
          <div>
            <dt>Coverage and confidence are separate</dt>
            <dd>
              Coverage is how much of an assessment is supported. Confidence is
              how good that support is. Complete-and-weak and
              incomplete-and-strong are both real, and one number cannot say
              both.
            </dd>
          </div>
          <div>
            <dt>No score is shown unless the evidence carries it</dt>
            <dd>
              Publication requires every material input to be supported. Today
              that means no organisation in the estate has a published score,
              and the product says so rather than showing a number.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="ai">
        <h2 id="ai">What the AI may and may not do</h2>
        <dl>
          <div>
            <dt>AI may propose. It may not confirm.</dt>
            <dd>
              Every automated writer records its output as proposed. Only a
              signed-in reviewer with the relevant permission can mark
              provenance confirmed.
            </dd>
          </div>
          <div>
            <dt>Model output is labelled as model output</dt>
            <dd>
              A model reading a document produces an inferred assessment, not a
              measurement — however good the source. Modelled values are marked
              as such and cannot be relabelled by hand.
            </dd>
          </div>
          <div>
            <dt>No AI module is claimed as production</dt>
            <dd>
              None has a measured evaluation, and for a generative system
              output quality is precisely what an evaluation measures. The
              production modules are deterministic engines.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="security">
        <h2 id="security">Security and access</h2>
        <dl>
          <div>
            <dt>Authentication</dt>
            <dd>
              Django sessions over HTTPS, with Secure and HttpOnly cookies in
              production and CSRF protection on every state-changing request.
            </dd>
          </div>
          <div>
            <dt>Staff access is enforced server-side</dt>
            <dd>
              What the browser is told about permissions is a rendering hint.
              Every restricted surface checks the session itself.
            </dd>
          </div>
          <div>
            <dt>Secrets</dt>
            <dd>
              Credentials are held in environment configuration and scanned for
              on every commit.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="not-yet">
        <h2 id="not-yet">What is not in place</h2>
        <p>
          Stated plainly, because a trust page that lists only strengths is not
          a trust page.
        </p>
        <ul>
          <li>
            <strong>No certifications.</strong> EcoIQ is not SOC 2 audited, not
            ISO certified, and there is no such thing as GDPR certification.
            Any of those claims would be false.
          </li>
          <li>
            <strong>No formal AI evaluation yet.</strong> No LLM-backed module
            has measured citation precision, groundedness or hallucination
            rate. Those modules are marked Beta or Experimental accordingly.
          </li>
          <li>
            <strong>Contradiction detection is not implemented.</strong> Nothing
            currently records that two sources disagree.
          </li>
          <li>
            <strong>Data retention policy is not yet published.</strong>
          </li>
        </ul>
      </section>
    </div>
  );
}
