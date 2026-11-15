package tn.esprit.awd.candidature.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import tn.esprit.awd.candidature.entity.Application;
import tn.esprit.awd.candidature.entity.Application.Status;

import java.time.LocalDate;

public record ApplicationDto(Long id, Long candidateId, Long jobId, LocalDate applicationDate,
                             String motivation, Status status) {
    public static ApplicationDto from(Application application) {
        return new ApplicationDto(application.getId(), application.getCandidateId(), application.getJobId(),
                application.getApplicationDate(), application.getMotivation(), application.getStatus());
    }

    public record Create(@NotNull @Positive Long candidateId, @NotNull @Positive Long jobId,
                         @Size(max = 2000) String motivation, LocalDate applicationDate) {
    }

    public record Update(@Size(max = 2000) String motivation, @NotNull LocalDate applicationDate) {
    }

    public record StatusUpdate(@NotNull Status status) {
    }
}
