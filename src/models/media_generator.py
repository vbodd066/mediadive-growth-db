"""
Media-composition generator (VAE-based).

Goal: learn a latent space of viable media compositions, then sample from it
conditioned on desired growth properties or strain characteristics.

Phase 1: Unconditional VAE over media composition vectors.
Phase 2: Conditional VAE — condition on strain/taxonomic embeddings.
Phase 3: Integrate metagenomic features as conditioning signal.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from src.models.base import BaseModel

log = logging.getLogger(__name__)


class MediaVAE(BaseModel):
    """
    Variational Autoencoder over media-composition vectors.

    Learns to reconstruct media recipes through a bottleneck,
    giving us a smooth latent space we can sample from to
    propose novel media formulations.
    """

    name = "media_vae"

    def __init__(
        self,
        input_dim: int = 0,
        latent_dim: int = 32,
        hidden_dims: list[int] | None = None,
        beta: float = 1.0,
        lr: float = 1e-3,
    ) -> None:
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.hidden_dims = hidden_dims or [256, 128]
        self.beta = beta  # KL weighting (β-VAE)
        self.lr = lr
        self._model: Any = None

    def _build(self) -> None:
        import torch
        import torch.nn as nn

        # ── Encoder ──
        enc_layers: list[nn.Module] = []
        prev = self.input_dim
        for h in self.hidden_dims:
            enc_layers += [nn.Linear(prev, h), nn.ReLU(), nn.BatchNorm1d(h)]
            prev = h
        self._encoder = nn.Sequential(*enc_layers)
        self._mu = nn.Linear(prev, self.latent_dim)
        self._logvar = nn.Linear(prev, self.latent_dim)

        # ── Decoder ──
        dec_layers: list[nn.Module] = []
        prev = self.latent_dim
        for h in reversed(self.hidden_dims):
            dec_layers += [nn.Linear(prev, h), nn.ReLU(), nn.BatchNorm1d(h)]
            prev = h
        dec_layers.append(nn.Linear(prev, self.input_dim))
        dec_layers.append(nn.ReLU())  # concentrations are non-negative
        self._decoder = nn.Sequential(*dec_layers)

        # Wrap into single module for save/load
        self._model = nn.ModuleDict(
            {
                "encoder": self._encoder,
                "mu": self._mu,
                "logvar": self._logvar,
                "decoder": self._decoder,
            }
        )

    def _reparameterize(self, mu: Any, logvar: Any) -> Any:
        import torch

        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def _forward(self, x: Any) -> tuple[Any, Any, Any]:
        h = self._encoder(x)
        mu = self._mu(h)
        logvar = self._logvar(h)
        z = self._reparameterize(mu, logvar)
        recon = self._decoder(z)
        return recon, mu, logvar

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray | None = None,  # unused for unconditional VAE
        X_val: np.ndarray | None = None,
        epochs: int = 200,
        batch_size: int = 64,
        **kwargs: Any,
    ) -> dict[str, list[float]]:
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        self.input_dim = X_train.shape[1]
        self._build()

        device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        self._model.to(device)  # type: ignore[union-attr]
        log.info("Training VAE on %s  latent=%d  epochs=%d", device, self.latent_dim, epochs)

        optimizer = torch.optim.AdamW(self._model.parameters(), lr=self.lr)  # type: ignore[union-attr]
        train_ds = TensorDataset(torch.tensor(X_train, dtype=torch.float32))
        train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        history: dict[str, list[float]] = {"train_loss": [], "recon_loss": [], "kl_loss": []}

        for epoch in range(1, epochs + 1):
            self._model.train()  # type: ignore[union-attr]
            total_loss = total_recon = total_kl = 0.0

            for (xb,) in train_dl:
                xb = xb.to(device)
                recon, mu, logvar = self._forward(xb)

                recon_loss = torch.nn.functional.mse_loss(recon, xb, reduction="sum")
                kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
                loss = recon_loss + self.beta * kl_loss

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                total_recon += recon_loss.item()
                total_kl += kl_loss.item()

            n = len(train_ds)
            history["train_loss"].append(total_loss / n)
            history["recon_loss"].append(total_recon / n)
            history["kl_loss"].append(total_kl / n)

            if epoch % 20 == 0 or epoch == 1:
                log.info(
                    "Epoch %3d/%d  loss=%.4f  recon=%.4f  kl=%.4f",
                    epoch, epochs,
                    total_loss / n, total_recon / n, total_kl / n,
                )

        return history

    def encode(self, X: np.ndarray) -> np.ndarray:
        """Encode media vectors into latent space."""
        import torch

        self._model.eval()  # type: ignore[union-attr]
        device = next(self._model.parameters()).device  # type: ignore[union-attr]
        with torch.no_grad():
            xt = torch.tensor(X, dtype=torch.float32).to(device)
            h = self._encoder(xt)
            mu = self._mu(h)
            return mu.cpu().numpy()

    def decode(self, z: np.ndarray) -> np.ndarray:
        """Decode latent vectors back to media composition space."""
        import torch

        self._model.eval()  # type: ignore[union-attr]
        device = next(self._model.parameters()).device  # type: ignore[union-attr]
        with torch.no_grad():
            zt = torch.tensor(z, dtype=torch.float32).to(device)
            return self._decoder(zt).cpu().numpy()

    def generate(self, n_samples: int = 10) -> np.ndarray:
        """Sample novel media compositions from the learned prior."""
        z = np.random.randn(n_samples, self.latent_dim).astype(np.float32)
        return self.decode(z)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Reconstruct input (autoencoder mode)."""
        import torch

        self._model.eval()  # type: ignore[union-attr]
        device = next(self._model.parameters()).device  # type: ignore[union-attr]
        with torch.no_grad():
            xt = torch.tensor(X, dtype=torch.float32).to(device)
            recon, _, _ = self._forward(xt)
            return recon.cpu().numpy()

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Not applicable for VAE — returns reconstruction."""
        return self.predict(X)

    def save(self, path: Path) -> None:
        import torch

        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self._model.state_dict(),  # type: ignore[union-attr]
                "input_dim": self.input_dim,
                "latent_dim": self.latent_dim,
                "hidden_dims": self.hidden_dims,
                "beta": self.beta,
                "lr": self.lr,
            },
            path,
        )
        log.info("Saved VAE → %s", path)

    @classmethod
    def load(cls, path: Path) -> "MediaVAE":
        import torch

        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        obj = cls(
            input_dim=ckpt["input_dim"],
            latent_dim=ckpt["latent_dim"],
            hidden_dims=ckpt["hidden_dims"],
            beta=ckpt["beta"],
            lr=ckpt["lr"],
        )
        obj._build()
        obj._model.load_state_dict(ckpt["state_dict"])  # type: ignore[union-attr]
        log.info("Loaded VAE ← %s", path)
        return obj

# ═══════════════════════════════════════════════════════════════
#  CVAE — Conditional VAE with Genome Conditioning
# ═══════════════════════════════════════════════════════════════


class ConditionalMediaVAE(BaseModel):
    """
    Conditional Variational Autoencoder for media generation.

    Conditions on genome embeddings to generate viable media formulations.
    Supports curriculum learning: train on bacteria first, then archea, fungi, etc.

    Architecture:
        - Encoder: (media_composition, genome_embedding) → (μ, σ)
        - Decoder: (z, genome_embedding) → media_composition

    The genome embedding acts as a powerful conditioning signal,
    allowing the model to learn organism-specific media preferences.
    """

    name = "conditional_media_vae"

    def __init__(
        self,
        input_dim: int = 0,
        condition_dim: int = 256,  # genome embedding dimension
        latent_dim: int = 32,
        hidden_dims: list[int] | None = None,
        beta: float = 1.0,
        lr: float = 1e-3,
        curriculum_phases: list[str] | None = None,
    ) -> None:
        self.input_dim = input_dim  # media composition dim
        self.condition_dim = condition_dim  # genome embedding dim
        self.latent_dim = latent_dim
        self.hidden_dims = hidden_dims or [256, 128]
        self.beta = beta
        self.lr = lr
        self.curriculum_phases = curriculum_phases or ["bacteria"]  # organism types to train on
        self._model: Any = None

    def _build(self) -> None:
        import torch
        import torch.nn as nn

        # ── Encoder: (media + condition) → latent ──
        enc_input_dim = self.input_dim + self.condition_dim
        enc_layers: list[nn.Module] = []
        prev = enc_input_dim

        for h in self.hidden_dims:
            enc_layers += [nn.Linear(prev, h), nn.ReLU(), nn.BatchNorm1d(h)]
            prev = h

        self._encoder = nn.Sequential(*enc_layers)
        self._mu = nn.Linear(prev, self.latent_dim)
        self._logvar = nn.Linear(prev, self.latent_dim)

        # ── Decoder: (latent + condition) → media ──
        dec_input_dim = self.latent_dim + self.condition_dim
        dec_layers: list[nn.Module] = []
        prev = dec_input_dim

        for h in reversed(self.hidden_dims):
            dec_layers += [nn.Linear(prev, h), nn.ReLU(), nn.BatchNorm1d(h)]
            prev = h

        dec_layers.append(nn.Linear(prev, self.input_dim))
        dec_layers.append(nn.ReLU())  # concentrations are non-negative
        self._decoder = nn.Sequential(*dec_layers)

        self._model = nn.ModuleDict(
            {
                "encoder": self._encoder,
                "mu": self._mu,
                "logvar": self._logvar,
                "decoder": self._decoder,
            }
        )

    def _reparameterize(self, mu: Any, logvar: Any) -> Any:
        import torch

        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def _forward(self, x: Any, c: Any) -> tuple[Any, Any, Any]:
        """Forward pass with conditioning."""
        # Concatenate media and condition
        xc = torch.cat([x, c], dim=1)
        h = self._encoder(xc)
        mu = self._mu(h)
        logvar = self._logvar(h)
        z = self._reparameterize(mu, logvar)

        # Decoder takes latent + condition
        zc = torch.cat([z, c], dim=1)
        recon = self._decoder(zc)

        return recon, mu, logvar

    def fit(
        self,
        X_train: np.ndarray,
        X_train_condition: np.ndarray,
        y_train: np.ndarray | None = None,
        X_val: np.ndarray | None = None,
        X_val_condition: np.ndarray | None = None,
        epochs: int = 200,
        batch_size: int = 64,
        curriculum_epoch: int = 0,
        curriculum_phase: str | None = None,
        **kwargs: Any,
    ) -> dict[str, list[float]]:
        """
        Train the CVAE.

        Args:
            X_train: Media composition vectors (n_samples, input_dim)
            X_train_condition: Genome embeddings (n_samples, condition_dim)
            y_train: Optional labels (organism type for curriculum tracking)
            X_val: Validation media
            X_val_condition: Validation genome embeddings
            epochs: Number of training epochs
            batch_size: Batch size
            curriculum_epoch: Current epoch in curriculum learning
            curriculum_phase: Name of current curriculum phase (e.g., "bacteria")
        """
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        self.input_dim = X_train.shape[1]
        self.condition_dim = X_train_condition.shape[1]
        self._build()

        device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        self._model.to(device)  # type: ignore[union-attr]

        phase_str = f" [{curriculum_phase}]" if curriculum_phase else ""
        log.info(
            "Training CVAE on %s  latent=%d  condition=%d  epochs=%d%s",
            device,
            self.latent_dim,
            self.condition_dim,
            epochs,
            phase_str,
        )

        optimizer = torch.optim.AdamW(self._model.parameters(), lr=self.lr)  # type: ignore[union-attr]
        train_ds = TensorDataset(
            torch.tensor(X_train, dtype=torch.float32),
            torch.tensor(X_train_condition, dtype=torch.float32),
        )
        train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        history: dict[str, list[float]] = {"train_loss": [], "recon_loss": [], "kl_loss": []}

        for epoch in range(1, epochs + 1):
            self._model.train()  # type: ignore[union-attr]
            total_loss = total_recon = total_kl = 0.0

            for xb, cb in train_dl:
                xb = xb.to(device)
                cb = cb.to(device)

                recon, mu, logvar = self._forward(xb, cb)

                recon_loss = torch.nn.functional.mse_loss(recon, xb, reduction="sum")
                kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
                loss = recon_loss + self.beta * kl_loss

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                total_recon += recon_loss.item()
                total_kl += kl_loss.item()

            n = len(train_ds)
            history["train_loss"].append(total_loss / n)
            history["recon_loss"].append(total_recon / n)
            history["kl_loss"].append(total_kl / n)

            if epoch % 20 == 0 or epoch == 1:
                log.info(
                    "Epoch %3d/%d  loss=%.4f  recon=%.4f  kl=%.4f%s",
                    epoch,
                    epochs,
                    total_loss / n,
                    total_recon / n,
                    total_kl / n,
                    phase_str,
                )

        return history

    def encode(self, X: np.ndarray, C: np.ndarray) -> np.ndarray:
        """Encode (media, condition) pairs into latent space."""
        import torch

        self._model.eval()  # type: ignore[union-attr]
        device = next(self._model.parameters()).device  # type: ignore[union-attr]

        with torch.no_grad():
            xt = torch.tensor(X, dtype=torch.float32).to(device)
            ct = torch.tensor(C, dtype=torch.float32).to(device)
            xc = torch.cat([xt, ct], dim=1)
            h = self._encoder(xc)
            mu = self._mu(h)
            return mu.cpu().numpy()

    def decode(self, z: np.ndarray, C: np.ndarray) -> np.ndarray:
        """Decode latent vectors + conditions back to media composition space."""
        import torch

        self._model.eval()  # type: ignore[union-attr]
        device = next(self._model.parameters()).device  # type: ignore[union-attr]

        with torch.no_grad():
            zt = torch.tensor(z, dtype=torch.float32).to(device)
            ct = torch.tensor(C, dtype=torch.float32).to(device)
            zc = torch.cat([zt, ct], dim=1)
            return self._decoder(zc).cpu().numpy()

    def generate(self, n_samples: int, condition: np.ndarray) -> np.ndarray:
        """
        Generate novel media compositions conditioned on genomes.

        Args:
            n_samples: Number of samples to generate
            condition: Genome embedding (1, condition_dim) to tile for all samples

        Returns:
            Generated media compositions (n_samples, input_dim)
        """
        z = np.random.randn(n_samples, self.latent_dim).astype(np.float32)
        c_tiled = np.tile(condition, (n_samples, 1))
        return self.decode(z, c_tiled)

    def predict(self, X: np.ndarray, C: np.ndarray) -> np.ndarray:
        """Reconstruct input (autoencoder mode with conditioning)."""
        import torch

        self._model.eval()  # type: ignore[union-attr]
        device = next(self._model.parameters()).device  # type: ignore[union-attr]

        with torch.no_grad():
            xt = torch.tensor(X, dtype=torch.float32).to(device)
            ct = torch.tensor(C, dtype=torch.float32).to(device)
            recon, _, _ = self._forward(xt, ct)
            return recon.cpu().numpy()

    def predict_proba(self, X: np.ndarray, C: np.ndarray) -> np.ndarray:
        """Not applicable for CVAE — returns reconstruction."""
        return self.predict(X, C)

    def save(self, path: Path) -> None:
        import torch

        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self._model.state_dict(),  # type: ignore[union-attr]
                "input_dim": self.input_dim,
                "condition_dim": self.condition_dim,
                "latent_dim": self.latent_dim,
                "hidden_dims": self.hidden_dims,
                "beta": self.beta,
                "lr": self.lr,
                "curriculum_phases": self.curriculum_phases,
            },
            path,
        )
        log.info("Saved CVAE → %s", path)

    @classmethod
    def load(cls, path: Path) -> "ConditionalMediaVAE":
        import torch

        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        obj = cls(
            input_dim=ckpt["input_dim"],
            condition_dim=ckpt["condition_dim"],
            latent_dim=ckpt["latent_dim"],
            hidden_dims=ckpt["hidden_dims"],
            beta=ckpt["beta"],
            lr=ckpt["lr"],
            curriculum_phases=ckpt.get("curriculum_phases"),
        )
        obj._build()
        obj._model.load_state_dict(ckpt["state_dict"])  # type: ignore[union-attr]
        log.info("Loaded CVAE ← %s", path)
        return obj