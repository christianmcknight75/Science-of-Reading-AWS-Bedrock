import { useState } from "react";
import { getRefresher } from "../api";
import { PageTitle } from "../app/router";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { RadioChips } from "../components/RadioChips";
import { Citations, SourceList, SourcesScope } from "../components/Sources";
import { TrainingNav } from "../components/TrainingNav";
import { Badge, Button, Card, ErrorMessage, ExampleChip } from "../components/ui";
import { useStored } from "../lib/storage";
import { useAsync } from "../lib/useAsync";

const FEEL = [
  { value: "not-sure", label: "Not sure" },
  { value: "getting-there", label: "Getting there" },
  { value: "got-it", label: "Got it" },
];

export default function Refreshers() {
  const { data, error, loading, retry } = useAsync(getRefresher, "refresher");
  const [answer, setAnswer] = useState<boolean | null>(null);
  // Self-rating is the teacher's own and stays on this device. It is never shown to anyone else.
  const [feel, setFeel] = useStored<Record<string, string>>("rh-feel", {});

  return (
    <>
      <TrainingNav current="/training/refreshers" />
      <PageTitle title="1-minute refreshers">Grow at your own pace</PageTitle>
      <p className="mt-2 text-lg text-muted">
        Training fades for everyone. That&apos;s normal. One minute a day keeps it fresh. Optional,
        and only you see this.
      </p>
      <div aria-live="polite" className="mt-5">
        {loading && (
          <p role="status" className="rh-pulse rounded-2xl border border-border bg-surface p-6">
            Loading today&apos;s refresher…
          </p>
        )}
        {error && <ErrorMessage onRetry={retry}>{error}</ErrorMessage>}
        {data && (
          <SourcesScope sources={data.sources} example={!!data.example}>
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <div className="flex flex-col gap-5">
                <Card aria-labelledby="today" className="border-2 border-primary">
                  <p className="text-sm font-bold uppercase tracking-wide text-muted">
                    Today&apos;s 1-minute refresher · Day {data.day} of keeping it fresh{" "}
                    {data.example && <ExampleChip />}
                  </p>
                  <h2 id="today" className="mt-2 font-heading text-2xl font-semibold">
                    &ldquo;{data.statement}&rdquo; True or not?
                  </h2>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      aria-pressed={answer === true}
                      variant={answer === true ? "primary" : "secondary"}
                      onClick={() => setAnswer(true)}
                    >
                      True
                    </Button>
                    <Button
                      aria-pressed={answer === false}
                      variant={answer === false ? "primary" : "secondary"}
                      onClick={() => setAnswer(false)}
                    >
                      Not true
                    </Button>
                  </div>
                  <div role="status" className="mt-4">
                    {answer !== null && (
                      <div className="rounded-lg bg-bg p-4">
                        <p className="font-semibold">
                          {answer === data.is_true ? "Yes, you've got it." : "Not quite."}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-3">
                          <Badge>Research says</Badge>
                          <EvidenceLabel label="Very sure" />
                        </div>
                        <p className="mt-2">
                          {data.explanation} <Citations ns={data.citations} />
                        </p>
                      </div>
                    )}
                  </div>
                </Card>

                <Card aria-labelledby="feel">
                  <h2 id="feel" className="font-heading text-xl font-semibold">
                    How sure do you feel teaching these?
                  </h2>
                  <p className="text-muted">
                    We use this to pick your refreshers. No one else sees it.
                  </p>
                  <div className="mt-3 flex flex-col gap-4">
                    {data.skills.map((s) => (
                      <RadioChips
                        key={s}
                        legend={s}
                        name={`feel-${s}`}
                        value={feel[s] ?? null}
                        onChange={(v) => setFeel({ ...feel, [s]: v })}
                        options={FEEL}
                      />
                    ))}
                  </div>
                </Card>

                <section aria-labelledby="picked">
                  <h2 id="picked" className="font-heading text-xl font-semibold">
                    Picked for you
                  </h2>
                  <ul className="mt-3 grid gap-4 md:grid-cols-2">
                    {data.picked.map((p) => (
                      <li key={p.title}>
                        <Card as="article" className="h-full">
                          <p className="text-sm text-muted">
                            {p.minutes} minutes · {p.kind}
                          </p>
                          <h3 className="font-heading text-lg font-semibold">{p.title}</h3>
                          <p>You get: {p.you_get}</p>
                        </Card>
                      </li>
                    ))}
                  </ul>
                </section>
              </div>
              <SourceList />
            </div>
          </SourcesScope>
        )}
      </div>
      <p className="mt-4 text-sm text-muted">
        Sample content. The sound clips and practice-out-loud refreshers are not built yet.
      </p>
    </>
  );
}
