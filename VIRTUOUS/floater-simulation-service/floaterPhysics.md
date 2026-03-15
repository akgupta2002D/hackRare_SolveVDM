# Floater Shadow Depth Model (Math Hypothesis)

## Variables

* `d`: normalized floater depth in the vitreous
* `S0`: intrinsic floater size
* `B0`: intrinsic floater blur
* `O0`: intrinsic floater opacity
* `S`: perceived shadow size on the retina
* `B`: perceived shadow blur on the retina
* `O`: perceived shadow opacity on the retina

## Coordinate System

`d ∈ [0,1]`

* `d = 0` → floater at the retina
* `d = 1` → floater near the lens / anterior vitreous

## Geometric Optics Intuition

Treat the floater as an occluding object between an incoming light field and the retina.
As the floater moves farther from the retina, the blocked light cone spreads before reaching the retina.
This should make the retinal shadow:

* larger
* blurrier
* less dark

## Shadow Size Model

Assume retinal shadow size grows linearly with depth: (An Assumption yet to be proven - next step) Here k1 basically controls the magnification.

`S = S0 (1 + k1 d)`

where `k1 > 0`.

Example with `S0 = 10 px`, `k1 = 1.5`:

* `d = 0.1` → `S = 11.5`
* `d = 0.5` → `S = 17.5`
* `d = 0.9` → `S = 23.5`

## Shadow Blur Model

Assume blur increases with distance because light scatter / penumbra width increases: (This is accurate in thoery but due to lack of understanding of floaters, this is based on my personal experience.)

`B = B0 + k2 d`

where `k2 > 0`.

Example with `B0 = 2`, `k2 = 6`:

* `d = 0.1` → `B = 2.6`
* `d = 0.5` → `B = 5.0`
* `d = 0.9` → `B = 7.4`

## Shadow Opacity Model

Assume shadow darkness decays with depth, following an exponential law. This reflects the physical intuition that as the floater moves farther from the retina, the fraction of blocked light falls off rapidly—not just linearly—since the diverging shadow lets more retinal area be illuminated. Exponential decay (using the natural base `e`) is a standard way to describe attenuation or loss processes in optics and vision science (e.g., light absorption, signal loss in tissues).

We model it as:

`O = O0 e^(-k3 d)`

where `k3 > 0`. The exponential ensures that shadow opacity decreases rapidly at first, then more gradually as `d` increases, matching the sort of falloff observed in light transmission through diffusive or scattering media.

Example with `O0 = 0.25`, `k3 = 1.2`:

* `d = 0.1` → `O ≈ 0.22`
* `d = 0.5` → `O ≈ 0.15`
* `d = 0.9` → `O ≈ 0.10`

## Complete Rendering Model

For each floater:

* `S = S0 (1 + k1 d)`
* `B = B0 + k2 d`
* `O = O0 e^(-k3 d)`

Floater shape stays fixed; depth changes spread, softness, and darkness.

## Inverse Model for User Drawings

Given a user-drawn size `S`:

`d_size = (S / S0 - 1) / k1`

Given a user-drawn blur `B`:

`d_blur = (B - B0) / k2`

A simple combined estimate:

`d_est = mean(d_size, d_blur)`

## Testable Prediction

If the model is directionally correct, then for the same floater:

* perceived size increases with depth
* perceived blur increases with depth
* perceived opacity decreases with depth

## Use in MVP

This model is a simple perceptual approximation, not a clinical model.
It is meant to support rendering and later comparison against user drawings.
