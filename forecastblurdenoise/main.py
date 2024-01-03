import argparse
import torch
from forecastblurdenoise.modules.transformer import Transformer
from forecastblurdenoise.data_loader import CustomDataLoader
from forecastblurdenoise.train_forecast_blur_denoise import TrainForecastBlurDenoise
from torch.utils.data import DataLoader, TensorDataset


class TimeSeriesDataset:
    def __init__(self, num_samples,
                 input_sequence_length,
                 output_sequence_length,
                 input_size,
                 output_size):
        self.num_samples = num_samples
        self.input_sequence_length = input_sequence_length
        self.output_sequence_length = output_sequence_length
        self.input_size = input_size
        self.output_size = output_size

        # input for encoder, input for decoder, and output (ground-truth)
        self.data = TensorDataset(torch.randn(self.num_samples, self.input_sequence_length, self.input_size),
                    torch.randn(self.num_samples, self.output_sequence_length, self.input_size),
                    torch.randn(self.num_samples, self.output_sequence_length, self.output_size))


def get_dataset(args, device):

    # Target column names for different datasets
    target_col = {"traffic": "values",
                  "electricity": "power_usage",
                  "exchange": "OT",
                  "solar": "Power(MW)",
                  "air_quality": "NO2",
                  "watershed": "Conductivity"}

    # Data loader configuration (replace with your own dataloader)
    data_loader = CustomDataLoader(exp_name=args.exp_name,
                                   max_encoder_length=args.max_encoder_length,
                                   pred_len=args.pred_len,
                                   target_col=target_col[args.exp_name],
                                   max_train_sample=args.max_train_sample,
                                   max_test_sample=args.max_test_sample,
                                   batch_size=args.batch_size,
                                   device=device,
                                   data_path=args.data_path)

    return data_loader


def main():
    """
    An example to execute the training and evaluation workflow for the forecasting and denoising model.
    """
    # Argument parser for configuring the training process
    parser = argparse.ArgumentParser(description="forecast-denoise argument parser")

    # Forecasting model parameters
    parser.add_argument("--attn_type", type=str, default='autoformer')
    parser.add_argument("--model_name", type=str, default="autoformer")
    parser.add_argument("--exp_name", type=str, default='exchange')
    parser.add_argument("--cuda", type=str, default="cuda:0")
    parser.add_argument("--noise_type", type=str, default="gp")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--pred_len", type=int, default=1234)
    parser.add_argument("--max_encoder_length", type=int, default=96)
    parser.add_argument("--max_decoder_length", type=int, default=96)
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--n_trials", type=int, default=50)
    parser.add_argument("--n_jobs", type=int, default=1)
    parser.add_argument("--num_inducing", type=int, default=1)
    parser.add_argument("--learning_residual", type=lambda x: str(x).lower() == "true", default="False")
    parser.add_argument("--no-noise", type=lambda x: str(x).lower() == "true", default="False")
    parser.add_argument("--add_noise_only_at_training", type=lambda x: str(x).lower() == "true", default="False")
    parser.add_argument("--num_epochs", type=int, default=5)
    parser.add_argument("--data_path", type=str, )

    args = parser.parse_args()

    # Device configuration
    device = torch.device(args.cuda if torch.cuda.is_available() else "cpu")

    if args.exp_name == "toy_data":
        # example parameters
        num_samples_train = 32
        num_samples_valid = 8
        num_samples_test = 8
        input_sequence_length = 96
        output_sequence_length = 96
        batch_size = 4
        input_size = 5
        output_size = 1

        train_dataset = TimeSeriesDataset(num_samples_train, input_sequence_length,
                                          output_sequence_length, input_size, output_size)
        valid_dataset = TimeSeriesDataset(num_samples_valid, input_sequence_length,
                                          output_sequence_length, input_size, output_size)
        test_dataset = TimeSeriesDataset(num_samples_test, input_sequence_length,
                                         output_sequence_length, input_size, output_size)

        train_loader = DataLoader(train_dataset.data, batch_size=batch_size, shuffle=True)
        valid_loader = DataLoader(valid_dataset.data, batch_size=batch_size, shuffle=False)
        test_loader = DataLoader(test_dataset.data, batch_size=batch_size, shuffle=False)

    else:
        data_loader = get_dataset(args, device)
        train_loader = data_loader.train_loader
        valid_loader = data_loader.valid_loader
        test_loader = data_loader.test_loader
        input_size = data_loader.input_size
        output_size = data_loader.output_size

    # Dimensionality of the model
    d_model = 32

    # Initializing the forecasting model (replace with your forecasting model)
    forecasting_model = Transformer(d_model=d_model,
                                    d_ff=d_model * 4,
                                    d_k=d_model, n_heads=8,
                                    n_layers=1, device=device,
                                    attn_type=args.attn_type,
                                    seed=1234).to(device)

    # Hyperparameter search space (change accordingly)
    hyperparameters = {"d_model": [16, 32], "n_heads": [1, 8],
                       "n_layers": [1, 2], "lr": [0.01, 0.001],
                       "num_inducing": [32, 64]}

    # Initializing and training the ForecastDenoise model using Optuna
    trainforecastdenoise = TrainForecastBlurDenoise(forecasting_model=forecasting_model,
                                                    train=train_loader,
                                                    valid=valid_loader,
                                                    test=test_loader,
                                                    noise_type="gp",
                                                    num_inducing=32,
                                                    add_noise_only_at_training=args.add_noise_only_at_training,
                                                    input_size=input_size,
                                                    output_size=output_size,
                                                    pred_len=96,
                                                    hyperparameters=hyperparameters,
                                                    seed=1234,
                                                    device=device)

    trainforecastdenoise.train()
    trainforecastdenoise.evaluate()


if __name__ == '__main__':
    main()
