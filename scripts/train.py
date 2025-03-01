import logging
import random
import time
from pathlib import Path

import hydra
import numpy as np
import torch
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig
from torch.utils.data import DataLoader
from torch.nn.functional import mse_loss

from trainer._version import __version__
from trainer import FModel
from trainer.train_dataset import train_dataset

log = logging.getLogger(__name__)

def _set_seed(cfg: DictConfig) -> None:
    torch.manual_seed(cfg.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(cfg.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    np.random.seed(cfg.np_seed)
    random.seed(cfg.seed)
    
def train(cfg, nn):
    dataset = train_dataset(cfg=cfg)
    
    dataloader = DataLoader(
        dataset=dataset,
        batch_size=cfg.train.batch_size,
        num_workers=0,
        collate_fn=dataset.collate_fn,
        drop_last=True,
    )
    
    lr = cfg.train.lr
    
    
    optimizer = torch.optim.Adam(params=nn.parameters(), lr=lr)
    
    # for epoch in range(start_epoch, cfg.train.epochs + 1):
    #     routing_model.epoch = epoch
    #     for i, hydrofabric in enumerate(dataloader, start=0):
    #         routing_model.mini_batch = i
            
    #         streamflow_predictions = flow(cfg=cfg, hydrofabric=hydrofabric)
    #         q_prime = streamflow_predictions["streamflow"] @ hydrofabric.transition_matrix
    #         spatial_params = nn(
    #             inputs=hydrofabric.normalized_spatial_attributes.to(cfg.device)
    #         )
    #         dmc_kwargs = {
    #             "hydrofabric": hydrofabric,
    #             "spatial_parameters": spatial_params,
    #             "streamflow": torch.tensor(q_prime, device=cfg.device, dtype=torch.float32)
    #         }
    #         dmc_output = routing_model(**dmc_kwargs)

    #         num_days = len(dmc_output["runoff"][0][13 : (-11 + cfg.params.tau)]) // 24
    #         daily_runoff = downsample(
    #             dmc_output["runoff"][:, 13 : (-11 + cfg.params.tau)],
    #             rho=num_days,
    #         )

    #         nan_mask = hydrofabric.observations.isnull().any(dim="time")
    #         np_nan_mask = nan_mask.streamflow.values

    #         filtered_ds = hydrofabric.observations.where(~nan_mask, drop=True)
    #         filtered_observations = torch.tensor(filtered_ds.streamflow.values, device=cfg.device, dtype=torch.float32)[
    #             :, 1:-1
    #         ]  # Cutting off days to match with realigned timesteps

    #         filtered_predictions = daily_runoff[~np_nan_mask]

    #         loss = mse_loss(
    #             input=filtered_predictions.transpose(0, 1)[cfg.train.warmup:].unsqueeze(2),
    #             target=filtered_observations.transpose(0, 1)[cfg.train.warmup:].unsqueeze(2),
    #         )

    #         log.info("Running backpropagation")

    #         loss.backward()
    #         optimizer.step()
    #         optimizer.zero_grad()
            
    #         np_pred = filtered_predictions.detach().cpu().numpy()
    #         np_target = filtered_observations.detach().cpu().numpy()
    #         plotted_dates = dataset.dates.batch_daily_time_range[
    #             1:-1
    #         ]
    #         metrics = Metrics(pred=np_pred, target=np_target)
    #         pred_nse = metrics.nse
    #         pred_nse_filtered = pred_nse[~np.isinf(pred_nse) & ~np.isnan(pred_nse)]
    #         median_nse = torch.tensor(pred_nse_filtered).median()
            
    #         # TODO: scale out when we have more gauges
    #         # random_index = np.random.randint(low=0, high=filtered_observations.shape[0], size=(1,))[0]
    #         random_gage = -1
    #         plot_time_series(
    #             filtered_predictions[-1].detach().cpu().numpy(),
    #             filtered_observations[-1].cpu().numpy(),
    #             plotted_dates,
    #             dataset.obs_reader.gage_dict["STAID"][random_gage],
    #             dataset.obs_reader.gage_dict["STANAME"][random_gage],
    #             metrics={"nse": pred_nse[-1]},
    #             path=cfg.params.save_path / f"plots/epoch_{epoch}_mb_{i}_validation_plot.png",
    #             warmup=cfg.train.warmup,
    #         )
            
    #         save_state(
    #             epoch=epoch,
    #             mini_batch=i,
    #             mlp=nn,
    #             optimizer=optimizer,
    #             name=cfg.name,
    #             saved_model_path=cfg.params.save_path / "saved_models",
    #         )
            
    #         print(f"Loss: {loss.item()}")
    #         print(f"Median NSE: {median_nse}")
    #         print(f"Median Mannings Roughness: {torch.median(routing_model.n.detach().cpu()).item()}")
        
    #     if epoch in cfg.train.learning_rate.keys():
    #         log.info(f"Updating learning rate: {cfg.train.learning_rate[epoch]}")
    #         for param_group in optimizer.param_groups:
    #             param_group["lr"] = cfg.train.learning_rate[epoch]



@hydra.main(
    version_base="1.3",
    config_path="../config",
    config_name="training_config",
)
def main(cfg: DictConfig) -> None:
    _set_seed(cfg=cfg)
    cfg.params.save_path = Path(HydraConfig.get().run.dir)
    (cfg.params.save_path / "plots").mkdir(exist_ok=True)
    (cfg.params.save_path / "saved_models").mkdir(exist_ok=True)
    try:
        start_time = time.perf_counter()
        nn = FModel()
        train(
            cfg=cfg,
            nn=nn
        )
        
    except KeyboardInterrupt:
        print("Keyboard interrupt received")
    
    finally:
        print("Cleaning up...")
    
        total_time = time.perf_counter() - start_time
        log.info(
            f"Time Elapsed: {(total_time / 60):.6f} minutes"
        ) 
        
if __name__ == "__main__":
    print(f"Training FModel with version: {__version__}")
    main()
