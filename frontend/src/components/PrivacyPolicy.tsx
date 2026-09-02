import { Fragment } from "react";

import {
  PRIVACY_POLICY,
  policyMeta,
  type PolicyBlock,
  type PolicyDocument,
  type PolicyRun,
} from "../lib/privacy-policy";

function renderRuns(runs: PolicyRun[]) {
  return runs.map((run, index) => (typeof run === "string"
    ? <Fragment key={index}>{run}</Fragment>
    : <strong key={index}>{run.strong}</strong>));
}

function PolicyBlockView({ block }: { block: PolicyBlock }) {
  if (block.kind === "list") {
    return (
      <ul className="policy__list">
        {block.items.map((item, index) => <li key={index}>{renderRuns(item)}</li>)}
      </ul>
    );
  }
  return (
    <p className={block.quiet ? "policy__text policy__text--quiet" : "policy__text"}>
      {renderRuns(block.runs)}
    </p>
  );
}

interface PrivacyPolicyProps {
  policy?: PolicyDocument;
}

/**
 * The full policy, rendered inside the app. A Mini App user who taps through
 * to it stays in the app instead of being handed to an external browser; the
 * same text is published at /privacy.html from the same source.
 */
export function PrivacyPolicy({ policy = PRIVACY_POLICY }: PrivacyPolicyProps) {
  return (
    <article className="policy">
      <p className="policy__meta">{policyMeta(policy)}</p>
      {policy.sections.map((section) => (
        <section className="policy__section" key={section.heading}>
          <h3>{section.heading}</h3>
          {section.blocks.map((block, index) => (
            <PolicyBlockView block={block} key={index} />
          ))}
        </section>
      ))}
    </article>
  );
}
