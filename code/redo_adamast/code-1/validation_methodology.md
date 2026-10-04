# Validation methodology

How is a taxonomy validated in the scenario of sampling a small amount of traces?

There are two things we need to address:

1. Do the failure modes we create cover all the types of failure instances possible on the full
   set? (Or at least to some degree of coverage.)
2. Are failure modes simply very general categories (e.g. Wrong Reasoning), or are they actually
   meaningful and insightful?

## Validation methods

For each of the two points, the method for validation:

1. After creating the taxonomy, do a full pass of the rest of the trace corpus (without the
   taxonomy) and identify all failure instances. Afterwards, have an independent annotator assign
   failure modes to the failure instances, while also leaving un-mapped ones blank. Calculate the
   ratio of mapped / total; if it is above a certain percentage, the taxonomy is validated.
2. Have a human annotator look at a set of traces and manually create a set of failure modes (or
   use something like TRAIL, or already annotated traces). Compare the generated taxonomy's
   failure modes with the ones created by the humans, and calculate their Cohen's Kappa.

## Topics to discuss

1. When randomly sampling a small set of traces from a full corpus, we run into the issue of some
   failure modes / instances simply not being available to the taxonomy generation. In this
   scenario, my proposal is to analyze "possible" failure instances, and based on those identify
   failure modes. The problem with this approach is that we risk creating a large number of
   failure modes that will never appear in reality. (E.g. see calculations made in traces, which
   are correct => Arithmetic Error; when analyzing the full corpus we discover that no trace
   displays any such errors.)
2. The other direction that can be considered is the online refinement aspect: if we anyway have
   a judge that goes over the other traces, when annotating, if it finds a failure instance that
   doesn't match any existing failure mode, it is allowed to edit the taxonomy and add it. For the
   initial iteration of this module, I propose the judge only be able to add codes, not edit or
   delete existing ones. We can maybe have a validation run after a set amount of traces / edits
   to the taxonomy has been made, in order to fix and optimize the taxonomy.
