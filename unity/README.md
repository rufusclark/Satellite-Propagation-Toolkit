# Unity

> ***Under Development***

This section of the project supports an effort to get a live SGP4 based model working within the unity game engine. This is intended to be used with AR/VR or large format projections.

## Methodology

Periodically generate cartesian position and velocity values from recent tracking data via CelesTrak (cached for a week) using SGP4 propagations. Then feed these values into Unity's physics engine and render the output.

This should be representatively accurate for visualisation purposes without needing to generate new SGP4 propagation data for each new frame rendered. Especially given SGP4 is only accurate to about 1km for a week.

## Code

The following code has been developed so far to support the cartesian vector coordinate generated so far.

* [Python based unity backend](unity_backend.py)
* [C# based unity backed](UnityScript/Program.cs)
