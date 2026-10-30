"""Optional offline neural network and text generator demos.

No external calls, real data, inference service or intervention permission.
PyTorch is optional and is NOT installed into the standard EcoIQ web runtime.
"""
from __future__ import annotations


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError("Install the optional CPU PyTorch training environment") from exc
    return torch, nn


def train_tiny_regression(*, steps: int = 75, seed: int = 11) -> dict[str, float]:
    """MLP with Linear -> Tanh -> Linear on invented y = 2*x + 1."""
    if not 1 <= steps <= 500:
        raise ValueError("steps must be between 1 and 500")
    torch, nn = _torch()
    torch.manual_seed(seed)
    x = torch.linspace(-1.0, 1.0, 32).unsqueeze(1)
    y = 2.0 * x + 1.0
    model = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 1))
    optimiser = torch.optim.Adam(model.parameters(), lr=0.04)
    loss_fn = nn.MSELoss()
    initial_loss = float(loss_fn(model(x), y).item())
    model.train()
    for _ in range(steps):
        optimiser.zero_grad(set_to_none=True)
        loss = loss_fn(model(x), y)
        loss.backward()
        optimiser.step()
    model.eval()
    with torch.no_grad():
        final_loss = float(loss_fn(model(x), y).item())
        prediction = float(model(torch.tensor([[0.5]])).item())
    return {
        "initial_training_mse": initial_loss,
        "final_training_mse": final_loss,
        "demo_prediction_for_x_0_5": prediction,
    }


def train_tiny_character_generator(*, steps: int = 25,
                                   max_new_tokens: int = 18,
                                   seed: int = 13) -> dict[str, object]:
    """Real tiny character generator: Embedding -> GRU -> Linear.

    Educational autoregression only; not an LLM or an operational finding.
    All tokens are from the artificial repeated 'eco iq' training string.
    """
    if not 1 <= steps <= 200 or not 1 <= max_new_tokens <= 64:
        raise ValueError("steps or max_new_tokens exceed educational limits")
    torch, nn = _torch()
    torch.manual_seed(seed)
    alphabet = " aceioqt"
    corpus = ("eco iq " * 35).strip()
    ids = {ch: i for i, ch in enumerate(alphabet)}
    encoded = torch.tensor([ids[ch] for ch in corpus], dtype=torch.long)
    inputs = encoded[:-1].unsqueeze(0)
    targets = encoded[1:].unsqueeze(0)

    class TinyGenerator(nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = nn.Embedding(len(alphabet), 12)
            self.gru = nn.GRU(12, 20, batch_first=True)
            self.output = nn.Linear(20, len(alphabet))

        def forward(self, tokens, hidden=None):
            states, hidden = self.gru(self.embedding(tokens), hidden)
            return self.output(states), hidden

    model = TinyGenerator()
    optimiser = torch.optim.Adam(model.parameters(), lr=0.025)
    model.train()
    for _ in range(steps):
        optimiser.zero_grad(set_to_none=True)
        logits, _ = model(inputs)
        loss = nn.functional.cross_entropy(
            logits.reshape(-1, len(alphabet)), targets.reshape(-1),
        )
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimiser.step()
    model.eval()
    chars = ["e"]
    current = torch.tensor([[ids["e"]]])
    hidden = None
    with torch.no_grad():
        for _ in range(max_new_tokens):
            logits, hidden = model(current, hidden)
            next_id = int(torch.argmax(logits[:, -1, :], dim=-1).item())
            chars.append(alphabet[next_id])
            current = torch.tensor([[next_id]], dtype=torch.long)
    return {
        "generated_sample": "".join(chars),
        "training_characters": len(corpus),
        "model_class": "Tiny autoregressive GRU (educational)",
        "trained_only_on_synthetic_data": True,
        "uses_external_api": False,
        "approved_for_customer_decisions": False,
    }
